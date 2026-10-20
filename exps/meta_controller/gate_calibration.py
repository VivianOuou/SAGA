"""
Offline gate calibration (no LLM calls): do the validation gates accept beneficial changes and reject
harmful ones? Pre-registered in PREREG_v4.md.

For every (task, probe change, seed):
  * ground truth: mock planner/analyzer with the task's initial objectives, real GA, in-process scorers.
    The probe is force-applied after iteration 1 (a validator that always prefers the candidate), the
    run continues to iteration GT_ITERS; the control run proposes no change. effect = test(probe) - test(control).
  * gate decisions: the same setup, the probe is proposed once after iteration 1 and judged by the real
    task validator with the OLD gate (single stage) and the NEW gate (sequential, up to 3 stages).
Labels use the mean effect over seeds: beneficial > +0.05, harmful < -0.05, otherwise neutral.

Two objective conditions (pre-registration amendment, see PREREG_v4.md):
  initial          - the task's initial objectives only
  planner_observed - the objective set the REAL planner used in iteration 1 of the v2/v2b/v3 A runs (seed 0)
Probes that are not applicable in a condition (e.g. adding an objective that is already present) are
reported as such and excluded from the gate statistics.

Usage (repository root):  python exps/meta_controller/gate_calibration.py --workers 2
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

GT_ITERS = 8
SEEDS = [0, 1, 2, 3, 4]
OLD_GATE = {"mode": "single", "min_improvement": 0.02}
NEW_GATE = {"mode": "sequential", "min_improvement": 0.02, "max_stages": 3, "reject_margin": -0.02,
            "adopt_candidate_population": True}


def _wf(**params):
    return ("optimization_workflow", {"params": params})


def _obj(name, direction, weight):
    return ("objective", {"ops": [{"op": "add_from_registry", "name": name, "optimization_direction": direction, "weight": weight}]})


def _san(objective, low, high):
    return ("implementation", {"objective_name": objective, "action": "sanitize_outputs", "valid_range": [low, high]})


# Objective sets used by the real gpt-5-mini planner in iteration 1 (runs ab-real_llm-<task>-s0-A-*).
PLANNER_OBSERVED = {
    "stagnant_search": {
        "performance": {
            "direction": "maximize",
            "weight": None
        },
        "distance_from_center": {
            "direction": "maximize",
            "weight": 0.5
        },
        "parameter_spread": {
            "direction": "maximize",
            "weight": 0.3
        }
    },
    "noisy_search": {
        "performance": {
            "direction": "maximize",
            "weight": None
        },
        "distance_from_center": {
            "direction": "maximize",
            "weight": 0.3
        },
        "parameter_spread": {
            "direction": "maximize",
            "weight": 0.2
        }
    },
    "frozen_mutation": {
        "performance": {
            "direction": "maximize",
            "weight": None
        },
        "distance_from_center": {
            "direction": "maximize",
            "weight": 0.3
        },
        "parameter_spread": {
            "direction": "maximize",
            "weight": 0.2
        }
    },
    "overflow_scorer": {
        "quality_score": {
            "direction": "maximize",
            "weight": None
        },
        "parameter_mean": {
            "direction": "maximize",
            "weight": 0.5
        },
        "parameter_spread": {
            "direction": "minimize",
            "weight": 0.5
        }
    },
    "underflow_cost": {
        "design_cost": {
            "direction": "minimize",
            "weight": None
        },
        "parameter_spread": {
            "direction": "minimize",
            "weight": 0.25
        }
    },
    "offset_scorer": {
        "quality_score": {
            "direction": "maximize",
            "weight": None
        },
        "parameter_mean": {
            "direction": "maximize",
            "weight": 1.0
        },
        "parameter_spread": {
            "direction": "maximize",
            "weight": 0.5
        }
    }
}
CONDITIONS = ("initial", "planner_observed")

PROBES = {
    "stagnant_search": {"fix:mutation_sigma=0.08": _wf(mutation_sigma=0.08), "random_candidate_ratio=0.5": _wf(random_candidate_ratio=0.5),
                        "add parameter_spread max w5": _obj("parameter_spread", "maximize", 5.0)},
    "noisy_search": {"fix:mutation_sigma=0.05": _wf(mutation_sigma=0.05), "tournament_size=2": _wf(tournament_size=2),
                     "add distance_from_center min w5": _obj("distance_from_center", "minimize", 5.0)},
    "frozen_mutation": {"fix:mutation_prob=0.3": _wf(mutation_prob=0.3), "mutation_sigma=0.3": _wf(mutation_sigma=0.3),
                        "add parameter_spread max w5": _obj("parameter_spread", "maximize", 5.0)},
    "overflow_scorer": {"fix:sanitize[0,1]": _san("quality_score", 0.0, 1.0), "sanitize[0,0.3]": _san("quality_score", 0.0, 0.3),
                        "mutation_sigma=0.3": _wf(mutation_sigma=0.3)},
    "underflow_cost": {"fix:sanitize[0,1]": _san("design_cost", 0.0, 1.0), "sanitize[0.5,1]": _san("design_cost", 0.5, 1.0),
                       "add parameter_mean max w5": _obj("parameter_mean", "maximize", 5.0)},
    "offset_scorer": {"fix:sanitize[0,1]": _san("quality_score", 0.0, 1.0), "sanitize[0,0.3]": _san("quality_score", 0.0, 0.3),
                      "add parameter_spread min w1": _obj("parameter_spread", "minimize", 1.0)},
}


def _run_job(job):
    """Run one orchestrator in a fresh working directory; returns a result dict."""
    from scileo_agent.core.config import FrameworkConfig, ModuleConfig
    from scileo_agent.core.data_models import Candidate, Population
    from scileo_agent.core.orchestrator import OptimizationOrchestrator
    from scileo_agent.core.registry.scorer_registry import reset_scorer_manager
    from scileo_agent.utils.logging import setup_logging
    from modules.shared import knowledge_manager, scorer_creator  # noqa: F401
    from modules.numeric_tasks import mocks, numeric_ga_optimizer, vector_serializer  # noqa: F401
    from modules.numeric_tasks.inprocess import register_inprocess_scorers
    from modules.numeric_tasks.tasks import TASKS, initial_population_vectors
    from modules.numeric_tasks.validators import get_numeric_validator, register_numeric_validators

    setup_logging(level="ERROR")
    register_numeric_validators()
    task = TASKS[job["task"]]
    seed = job["seed"]
    workdir = tempfile.mkdtemp(prefix="gatecal_", dir=job["tmp_root"])
    os.chdir(workdir)
    try:
        reset_scorer_manager()
        register_inprocess_scorers(task.task_id)
        if job["condition"] == "planner_observed":
            objectives = PLANNER_OBSERVED[task.task_id]
        else:
            objectives = {n: (d or "filter") for n, d in task.initial_objectives.items()}
        ga = dict(dim=task.dim, pop_size=32, generations=10, seed=seed, **task.optimizer_overrides)
        modules = {
            "planner": ModuleConfig(module_id="planner", module_type="planner", module_name="mock_rule_planner",
                                    config={"objectives": objectives, "support_filter": True}, llm_config=None),
            "scorer_creator": ModuleConfig(module_id="scorer_creator", module_type="scorer_creator", module_name="general_scorer_creator",
                                           config={"enable_llm_scorer_creation": False, "enable_llm_matching": False}, llm_config=None),
            "optimizer": ModuleConfig(module_id="optimizer", module_type="optimizer", module_name="numeric_ga_optimizer", config=ga, llm_config=None),
            "analyzer": ModuleConfig(module_id="analyzer", module_type="analyzer", module_name="mock_stats_analyzer", config={}, llm_config=None),
            "knowledge_manager": ModuleConfig(module_id="knowledge_manager", module_type="knowledge_manager",
                                              module_name="basic_knowledge_manager", config={}, llm_config=None),
        }
        validation = dict(job["gate"], seeds=[1000 * (seed + 1), 1000 * (seed + 1) + 1], trial_optimizer_overrides={}, seed_key="seed")
        loop = {"max_iterations": job["iterations"], "run_scorers_in_docker": False, "random_candidate_ratio": 0.0,
                "return_all_candidates": False, "stop_on_analyzer_decision": False, **task.loop_overrides,
                "meta_controller": {"enabled": True, "task_id": task.task_id, "seed": seed, "judge": {"type": "none"},
                                    "validator": task.validator, "validation": validation, "max_ops_per_change": 1}}
        orch = OptimizationOrchestrator(FrameworkConfig(loop_config=loop, modules=modules), run_name="gatecal", run_id="gatecal")
        target, change = job["probe"] if job["probe"] else ("no_change", None)
        orch.meta_controller.set_judge(mocks.ScriptedJudge([mocks.decision(target, change)]))
        if job["force_accept"]:  # ground truth: the probe is applied regardless of its validation result
            orch.meta_controller.validator = mocks.ScriptedValidator([0.0, 0.0, 1.0, 1.0])
        population = Population(candidates=[Candidate(representation=v) for v in initial_population_vectors(task.dim, 32, seed)])
        t0 = time.time()
        asyncio.run(orch.run(high_level_goal=task.goal, context_information=task.context,
                             serializer_name="vector_serializer", initial_population=population))
        record = orch.meta_controller.records[0]
        test = get_numeric_validator(task.validator).evaluate([c.representation for c in orch.current_population.candidates], split="test")
        v = record.get("validation") or {}
        return {**{k: job[k] for k in ("kind", "condition", "task", "label", "seed", "gate_name")}, "outcome": record["outcome"],
                "reason": record["reason"][:160], "stages": len(v.get("stages", [])) or (1 if v.get("delta") is not None else 0),
                "delta": v.get("delta"), "test_metric": test.metric,
                "decision_evals": (record["costs"].get("candidate", {}).get("oracle_evals") or 0)
                + (record["costs"].get("validation", {}).get("oracle_evals") or 0),
                "seconds": round(time.time() - t0, 1)}
    finally:
        os.chdir(ROOT)
        shutil.rmtree(workdir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--out", default=str(ROOT / "exps" / "meta_controller" / "results" / "v4" / "gate_calibration"))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp_root = tempfile.mkdtemp(prefix="gatecal_root_")
    jobs = []
    for condition in CONDITIONS:
        for task, probes in PROBES.items():
            for seed in SEEDS:
                base = {"condition": condition, "task": task, "seed": seed, "tmp_root": tmp_root}
                jobs.append(dict(base, kind="ground_truth", label="control:no_change", probe=None, gate=OLD_GATE, gate_name="-",
                                 force_accept=False, iterations=GT_ITERS))
                for label, probe in probes.items():
                    jobs.append(dict(base, kind="ground_truth", label=label, probe=probe, gate=OLD_GATE, gate_name="-",
                                     force_accept=True, iterations=GT_ITERS))
                    for gate_name, gate in (("old", OLD_GATE), ("new", NEW_GATE)):
                        jobs.append(dict(base, kind="gate", label=label, probe=probe, gate=gate, gate_name=gate_name,
                                         force_accept=False, iterations=2))
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool, open(out / "runs.jsonl", "w") as f:
        for i, r in enumerate(pool.map(_run_job, jobs), 1):
            results.append(r)
            f.write(json.dumps(r) + "\n")
            f.flush()
            if i % 20 == 0:
                print(f"{i}/{len(jobs)} jobs done", flush=True)
    shutil.rmtree(tmp_root, ignore_errors=True)
    summarize(results, out)


def summarize(results, out: Path):
    import numpy as np
    gt = {(r["condition"], r["task"], r["label"], r["seed"]): r for r in results if r["kind"] == "ground_truth"}
    probes = []
    for condition in CONDITIONS:
      for task, ps in PROBES.items():
        for label in ps:
            applied = [gt[(condition, task, label, s)]["outcome"] == "accepted" for s in SEEDS]
            effects = [gt[(condition, task, label, s)]["test_metric"] - gt[(condition, task, "control:no_change", s)]["test_metric"] for s in SEEDS]
            mean = float(np.mean(effects))
            cls = ("not_applicable" if not all(applied) else
                   "beneficial" if mean > 0.05 else "harmful" if mean < -0.05 else "neutral")
            row = {"condition": condition, "task": task, "probe": label, "true_effect_mean": round(mean, 3),
                   "true_effect_per_seed": [round(e, 3) for e in effects], "class": cls}
            for gate in ("old", "new"):
                gs = [r for r in results if r["kind"] == "gate" and r["condition"] == condition and r["task"] == task
                      and r["label"] == label and r["gate_name"] == gate]
                row[f"{gate}_accepted"] = sum(r["outcome"] == "accepted" for r in gs)
                row[f"{gate}_n"] = len(gs)
                row[f"{gate}_mean_stages"] = round(float(np.mean([r["stages"] for r in gs])), 2)
                row[f"{gate}_mean_decision_evals"] = round(float(np.mean([r["decision_evals"] for r in gs])), 0)
            probes.append(row)
    agg = {}
    for condition in CONDITIONS + ("all",):
        rows_c = [p for p in probes if condition == "all" or p["condition"] == condition]
        for gate in ("old", "new"):
            for cls in ("beneficial", "harmful", "neutral"):
                rows = [p for p in rows_c if p["class"] == cls]
                agg[f"{condition}|{gate}:{cls}"] = {"accepted": sum(p[f"{gate}_accepted"] for p in rows), "n": sum(p[f"{gate}_n"] for p in rows)}
            applicable = [p for p in rows_c if p["class"] != "not_applicable"]
            agg[f"{condition}|{gate}:mean_decision_evals"] = round(float(np.mean([p[f"{gate}_mean_decision_evals"] for p in applicable])), 0)
    summary = {"note": "OFFLINE, no LLM: mock planner/analyzer, real GA/controller/validators, in-process scorers",
               "gates": {"old": OLD_GATE, "new": NEW_GATE}, "probes": probes, "aggregate": agg}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    lines = ["# Gate calibration (offline, no LLM)", "", summary["note"], "",
             "| condition | task | probe | true effect (mean of 5 seeds) | class | old gate accepted | new gate accepted | new mean stages |",
             "|---|---|---|---|---|---|---|---|"]
    for p in probes:
        lines.append(f"| {p['condition']} | {p['task']} | {p['probe']} | {p['true_effect_mean']:+.3f} | {p['class']} | "
                     f"{p['old_accepted']}/{p['old_n']} | {p['new_accepted']}/{p['new_n']} | {p['new_mean_stages']} |")
    lines += ["", "| condition | gate | beneficial accepted | harmful accepted (false accept) | neutral accepted | mean evals per decision |",
              "|---|---|---|---|---|---|"]
    for condition in CONDITIONS + ("all",):
        for gate in ("old", "new"):
            b, h, n = (agg[f"{condition}|{gate}:{c}"] for c in ("beneficial", "harmful", "neutral"))
            lines.append(f"| {condition} | {gate} | {b['accepted']}/{b['n']} | {h['accepted']}/{h['n']} | {n['accepted']}/{n['n']} | "
                         f"{agg[f'{condition}|{gate}:mean_decision_evals']} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
