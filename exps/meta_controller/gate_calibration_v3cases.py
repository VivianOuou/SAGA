"""
Offline check on the v3 false-rejection cases (no LLM): for each offset_scorer sanitize fix that the old
gate rejected in v3 (arms B/E/F), take the exact objective set the real planner used in that iteration and
(1) measure the fix's long-run effect (forced application vs. no change, 8 iterations, 5 seeds) and
(2) count how often the OLD and NEW gates accept it (5 seeds).

Usage (repository root):  python exps/meta_controller/gate_calibration_v3cases.py
"""

import glob
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_calibration as g  # noqa: E402

R = ROOT / "exps" / "meta_controller" / "results" / "v3"


def rejected_cases():
    cases = []
    for arm in "BEF":
        for seed in (0, 1, 2):
            for line in open(R / f"real_llm__offset_scorer__s{seed}__{arm}.decisions.jsonl"):
                r = json.loads(line)
                d = r.get("decision") or {}
                if d.get("intervention_target") == "implementation" and r["outcome"] == "rejected":
                    run = sorted(glob.glob(str(ROOT / f"runs/ab-real_llm-offset_scorer-s{seed}-{arm}-*")))[-1]
                    t = json.load(open(f"{run}/outputs/run_process_tracking.json"))
                    it = [x for x in t["iterations"] if x["iteration_number"] == r["iteration"]][0]
                    objs = [p for p in it["phases"] if p["phase_name"] == "scorer_creation"][0]["outputs"]["objectives_with_scorers"]
                    cases.append((f"{arm} s{seed} it{r['iteration']}",
                                  {o["name"]: {"direction": o["optimization_direction"], "weight": o["weight"]} for o in objs}))
                    break
    return cases


def main():
    tmp = tempfile.mkdtemp()
    fix = g.PROBES["offset_scorer"]["fix:sanitize[0,1]"]
    rows, totals = [], {"old": 0, "new": 0}
    for label, objs in rejected_cases():
        g.PLANNER_OBSERVED["offset_scorer"] = objs
        base = dict(condition="planner_observed", task="offset_scorer", tmp_root=tmp)
        effects = []
        for seed in g.SEEDS:
            ctl = g._run_job(dict(base, seed=seed, kind="ground_truth", label="ctl", probe=None, gate=g.OLD_GATE, gate_name="-",
                                  force_accept=False, iterations=g.GT_ITERS))
            fx = g._run_job(dict(base, seed=seed, kind="ground_truth", label="fix", probe=fix, gate=g.OLD_GATE, gate_name="-",
                                 force_accept=True, iterations=g.GT_ITERS))
            effects.append(fx["test_metric"] - ctl["test_metric"])
        row = {"case": label, "objectives": objs, "long_run_effect_mean": round(float(np.mean(effects)), 3)}
        for gate_name, gate in (("old", g.OLD_GATE), ("new", g.NEW_GATE)):
            res = [g._run_job(dict(base, seed=s, kind="gate", label="fix", probe=fix, gate=gate, gate_name=gate_name,
                                   force_accept=False, iterations=2)) for s in g.SEEDS]
            row[f"{gate_name}_accepted"] = sum(r["outcome"] == "accepted" for r in res)
            row[f"{gate_name}_stages"] = [r["stages"] for r in res]
            row[f"{gate_name}_mean_evals"] = round(float(np.mean([r["decision_evals"] for r in res])))
            totals[gate_name] += row[f"{gate_name}_accepted"]
        rows.append(row)
        print(f"{label:12s} effect {row['long_run_effect_mean']:+.3f}  old {row['old_accepted']}/5  new {row['new_accepted']}/5 "
              f"(stages {row['new_stages']}, evals {row['new_mean_evals']})", flush=True)
    n = 5 * len(rows)
    print(f"TOTAL accepted: old {totals['old']}/{n}, new {totals['new']}/{n}")
    out = ROOT / "exps" / "meta_controller" / "results" / "v4" / "gate_calibration" / "v3_rejected_cases_gate.json"
    out.write_text(json.dumps({"gates": {"old": g.OLD_GATE, "new": g.NEW_GATE}, "rows": rows, "totals": totals, "n": n}, indent=1))


if __name__ == "__main__":
    main()
