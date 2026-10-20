"""
Supplementary false-accept check (added after the pre-registered calibration, before looking at its
own results): start from HEALTHY optimizer settings (the planted misconfiguration removed) and propose
changes expected to be harmful. Ground truth and gate decisions exactly as in gate_calibration.py.

Usage (repository root):  python exps/meta_controller/gate_calibration_harmful.py --workers 2
"""

import argparse
import json
import shutil
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_calibration as g  # noqa: E402

HARMFUL = {
    task: {"mutation_prob=0.0": g._wf(mutation_prob=0.0), "mutation_sigma=0.5": g._wf(mutation_sigma=0.5),
           "add parameter_spread max w5": g._obj("parameter_spread", "maximize", 5.0)}
    for task in ("stagnant_search", "noisy_search", "frozen_mutation")
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    out = ROOT / "exps" / "meta_controller" / "results" / "v4" / "gate_calibration"
    tmp = tempfile.mkdtemp(prefix="gatecal_h_")
    jobs = []
    for task, probes in HARMFUL.items():
        for seed in g.SEEDS:
            base = dict(condition="healthy", task=task, seed=seed, tmp_root=tmp, healthy=True)
            jobs.append(dict(base, kind="ground_truth", label="control:no_change", probe=None, gate=g.OLD_GATE, gate_name="-",
                             force_accept=False, iterations=g.GT_ITERS))
            for label, probe in probes.items():
                jobs.append(dict(base, kind="ground_truth", label=label, probe=probe, gate=g.OLD_GATE, gate_name="-",
                                 force_accept=True, iterations=g.GT_ITERS))
                for gate_name, gate in (("old", g.OLD_GATE), ("new", g.NEW_GATE)):
                    jobs.append(dict(base, kind="gate", label=label, probe=probe, gate=gate, gate_name=gate_name,
                                     force_accept=False, iterations=2))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(g._run_job, jobs))
    shutil.rmtree(tmp, ignore_errors=True)
    (out / "harmful_runs.jsonl").write_text("\n".join(json.dumps(r) for r in results) + "\n")
    gt = {(r["task"], r["label"], r["seed"]): r for r in results if r["kind"] == "ground_truth"}
    lines = ["# Supplementary false-accept check (healthy optimizer settings, offline, no LLM)", "",
             "| task | probe | true effect (mean of 5 seeds) | class | old gate accepted | new gate accepted |", "|---|---|---|---|---|---|"]
    tot = {"old": [0, 0], "new": [0, 0]}
    for task, probes in HARMFUL.items():
        for label in probes:
            eff = float(np.mean([gt[(task, label, s)]["test_metric"] - gt[(task, "control:no_change", s)]["test_metric"] for s in g.SEEDS]))
            cls = "harmful" if eff < -0.05 else "beneficial" if eff > 0.05 else "neutral"
            acc = {gn: sum(r["outcome"] == "accepted" for r in results if r["kind"] == "gate" and r["task"] == task
                           and r["label"] == label and r["gate_name"] == gn) for gn in ("old", "new")}
            if cls == "harmful":
                for gn in tot:
                    tot[gn][0] += acc[gn]; tot[gn][1] += 5
            lines.append(f"| {task} | {label} | {eff:+.3f} | {cls} | {acc['old']}/5 | {acc['new']}/5 |")
    lines += ["", f"Harmful changes accepted (false accepts): old {tot['old'][0]}/{tot['old'][1]}, new {tot['new'][0]}/{tot['new'][1]}"]
    (out / "harmful_summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
