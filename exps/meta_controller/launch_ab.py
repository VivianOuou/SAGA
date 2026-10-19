"""
Run the A/B grid (tasks x seeds x {A, B}) as independent subprocesses, resumable.

- Each cell runs exps/meta_controller/run_numeric_ab.py and writes its own result JSON.
- Cells whose result file already exists with status "completed" are skipped (resume after a crash).
- Progress is written to <results_dir>/grid_status.json after every state change, so completion can
  be checked without the launching shell (e.g. after an SSH disconnect).
- At the end, summarize_ab.py is run.

Usage (repository root, saga env, OPENAI_API_KEY exported):
    python exps/meta_controller/launch_ab.py --parallel 4
    python exps/meta_controller/launch_ab.py --offline-mock --parallel 2      # MOCK pipeline check
"""

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "exps" / "meta_controller"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=str(HERE / "ab_config.yaml"))
    parser.add_argument("--parallel", type=int, default=2)
    parser.add_argument("--offline-mock", action="store_true")
    parser.add_argument("--results-dir", default=str(HERE / "results"))
    args = parser.parse_args()
    cfg = yaml.safe_load(open(args.config))
    mode = "offline_mock" if args.offline_mock else "real_llm"
    results_dir = Path(args.results_dir) / ("offline_mock" if args.offline_mock else "")
    results_dir.mkdir(parents=True, exist_ok=True)
    log_dir = results_dir / "logs"
    log_dir.mkdir(exist_ok=True)

    cells = [(t, s, a) for t in cfg["tasks"] for s in cfg["seeds"] for a in ("A", "B")]
    status_path = results_dir / "grid_status.json"
    status = {f"{t}__s{s}__{a}": {"state": "pending"} for t, s, a in cells}

    def save():
        doc = {"mode": mode, "updated": datetime.now().isoformat(), "config": args.config,
               "done": sum(v["state"] == "done" for v in status.values()),
               "failed": sum(v["state"] == "failed" for v in status.values()),
               "total": len(status), "cells": status}
        tmp = status_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, indent=2))
        tmp.replace(status_path)

    def run_cell(cell):
        task, seed, arm = cell
        key = f"{task}__s{seed}__{arm}"
        result_file = results_dir / f"{mode}__{key}.json"
        if result_file.exists() and json.loads(result_file.read_text()).get("status") == "completed":
            status[key] = {"state": "done", "skipped_existing": True, "result": str(result_file)}
            save()
            return
        status[key] = {"state": "running", "started": datetime.now().isoformat()}
        save()
        cmd = [sys.executable, str(HERE / "run_numeric_ab.py"), "--task", task, "--seed", str(seed), "--arm", arm,
               "--config", args.config, "--results-dir", str(Path(args.results_dir)), "--log-level", "INFO"]
        if args.offline_mock:
            cmd.append("--offline-mock")
        t0 = time.time()
        with open(log_dir / f"{key}.log", "w") as log:
            proc = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        ok = proc.returncode == 0 and result_file.exists() and json.loads(result_file.read_text()).get("status") == "completed"
        status[key] = {"state": "done" if ok else "failed", "returncode": proc.returncode,
                       "seconds": round(time.time() - t0, 1), "log": str(log_dir / f"{key}.log"),
                       "result": str(result_file) if result_file.exists() else None}
        save()

    save()
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        list(pool.map(run_cell, cells))
    subprocess.run([sys.executable, str(HERE / "summarize_ab.py"), "--results-dir", str(results_dir), "--mode", mode], cwd=ROOT)
    print(json.dumps({k: v["state"] for k, v in status.items()}, indent=1))


if __name__ == "__main__":
    main()
