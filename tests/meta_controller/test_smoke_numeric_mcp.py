"""
Integration smoke test (SYNTHETIC task, MOCK planner/analyzer/judge, REAL MCP scorer subprocesses,
real orchestrator, GA, controller and validator). Proves the propose -> execute -> validate ->
accept/reject -> log chain runs end to end; it is not evidence about real LLM judges.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _run(repo_root, tmp_path, task, arm):
    cmd = [sys.executable, "exps/meta_controller/run_numeric_ab.py", "--task", task, "--seed", "0", "--arm", arm,
           "--offline-mock", "--results-dir", str(tmp_path), "--log-level", "WARNING", "--port-base", "41000" if arm == "A" else "41200"]
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    result = json.loads((tmp_path / "offline_mock" / f"offline_mock__{task}__s0__{arm}.json").read_text())
    return result


def test_offline_mock_pipeline_end_to_end(repo_root, tmp_path):
    a = _run(repo_root, tmp_path, "spectral_signal", "A")
    b = _run(repo_root, tmp_path, "spectral_signal", "B")
    for r in (a, b):
        assert r["mode"] == "offline_mock" and "MOCK" in r["evidence_note"]
        assert r["status"] == "completed" and r["test_metric"] is not None
        assert r["budget"]["caps"] and r["llm_calls"] is not None
    assert a["meta_controller"] is None
    summary = b["meta_controller"]
    assert summary["decisions"] >= 1 and summary["outcomes"].get("accepted", 0) + summary["outcomes"].get("rejected", 0) >= 1
    decisions = (tmp_path / "offline_mock" / "offline_mock__spectral_signal__s0__B.decisions.jsonl").read_text().splitlines()
    first = json.loads(decisions[0])
    assert first["decision"]["intervention_target"] == "implementation"
    assert first["validation"]["baseline"] and first["validation"]["candidate"]
    assert {"judge", "candidate", "validation", "total"} <= set(first["costs"])
    assert first["validator"]["name"] == "spectral_signal_truth" and first["acceptance_rule"]["split"] == "validation"
    for r in (a, b):
        shutil.rmtree(Path(repo_root) / r["run_dir"], ignore_errors=True)
