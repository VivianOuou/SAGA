"""
v5 (pre-registered in PREREG_v5.md): offline validator-realism study, no LLM calls.

Does the validation gate still block harmful changes, and do interventions still pay off, when the
validator is imperfect (noisy / biased / proxy-only) and when a validator evaluation costs 10x a
proxy evaluation?

Components: mock planner/analyzer (fixed objective set), real GA / Meta-Controller / sequential gate,
in-process proxy scorers. Judges:
  A    no controller (native loop, same budget)
  SIM  SimulatedJudge (MOCK): designated fix with p=0.6, otherwise a wrong or bug-exploiting change
  RND  RandomTargetJudge (control)
SIM and RND are crossed with 4 validator variants x 2 validation-cost multipliers x 2 gates x 2 budgets
(amendment 1). The reported test
metric always comes from the exact validator's test split, independent of the gate's validator.

Usage (repository root):
  python exps/meta_controller/validator_realism.py --workers 2            # ground truth + full grid
  python exps/meta_controller/validator_realism.py --smoke                # 1 task, 1 seed, quick check
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate_calibration import CONDITIONS, GT_ITERS, NEW_GATE, OLD_GATE, PLANNER_OBSERVED, PROBES, SEEDS, _run_job  # noqa: E402

VARIANTS = ("oracle", "noisy", "biased", "proxy")
COSTS = (1, 10)
# Amendment 1: two gates (v4, v4 + noise floor) and two eval budgets (v4's 5000, and 15000); mock LLM calls are fake -> not capped.
GATES = {"v4": NEW_GATE, "v4_floor": dict(NEW_GATE, reject_margin=0.005)}
BUDGETS = (5000, 15000)
MAX_ITERATIONS = 60
V4_SUMMARY = ROOT / "exps" / "meta_controller" / "results" / "v4" / "gate_calibration" / "summary.json"

# One bug-exploiting change per buggy task (pushes the population into the region where the proxy scorer is wrong).
KEY = ("arm", "variant", "cost", "gate", "budget", "condition", "task", "seed")
CONFIG = ("arm", "variant", "cost", "gate", "budget")

EXPLOITS = {
    "overflow_scorer": ("exploit:parameter_mean max w5", "parameter_mean", "maximize"),
    "underflow_cost": ("exploit:parameter_mean min w5", "parameter_mean", "minimize"),
    "offset_scorer": ("exploit:parameter_mean max w5", "parameter_mean", "maximize"),
}


def objective_names(condition, task_id):
    from modules.numeric_tasks.tasks import TASKS
    return set(PLANNER_OBSERVED[task_id] if condition == "planner_observed" else TASKS[task_id].initial_objectives)


def exploit_probe(condition, task_id):
    label, name, direction = EXPLOITS[task_id]
    if name in objective_names(condition, task_id):
        return label, ("objective", {"ops": [{"op": "set_weight", "name": name, "weight": 5.0}]})
    return label, ("objective", {"ops": [{"op": "add_from_registry", "name": name, "optimization_direction": direction, "weight": 5.0}]})


def v4_classes():
    probes = json.loads(V4_SUMMARY.read_text())["probes"]
    return {(p["condition"], p["task"], p["probe"]): p["class"] for p in probes}


def judge_menu(condition, task_id, classes):
    """(fix, wrong) for the simulated judge; probes not applicable in this condition are left out."""
    fix = next((label, probe) for label, probe in PROBES[task_id].items() if label.startswith("fix:"))
    wrong = {label: probe for label, probe in PROBES[task_id].items()
             if not label.startswith("fix:") and classes.get((condition, task_id, label)) != "not_applicable"}
    if task_id in EXPLOITS:
        label, probe = exploit_probe(condition, task_id)
        wrong[label] = probe
    return fix, wrong


def _run_e2e(job):
    """One full budget-limited run; returns final test metric, controller decisions and spend."""
    from scileo_agent.core.config import FrameworkConfig, ModuleConfig
    from scileo_agent.core.data_models import Candidate, Population
    from scileo_agent.core.orchestrator import OptimizationOrchestrator
    from scileo_agent.core.registry.scorer_registry import reset_scorer_manager
    from scileo_agent.utils.logging import setup_logging
    from modules.shared import knowledge_manager, scorer_creator  # noqa: F401
    from modules.numeric_tasks import mocks, numeric_ga_optimizer, vector_serializer  # noqa: F401
    from modules.numeric_tasks.inprocess import register_inprocess_scorers
    from modules.numeric_tasks.tasks import TASKS, initial_population_vectors
    from modules.numeric_tasks.validators import get_numeric_validator, make_realism_validator, register_numeric_validators

    import random

    import numpy as np

    setup_logging(level="ERROR")
    register_numeric_validators()
    task = TASKS[job["task"]]
    seed = job["seed"]
    random.seed(seed)
    np.random.seed(seed)
    workdir = tempfile.mkdtemp(prefix="valreal_", dir=job["tmp_root"])
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
        loop = {"max_iterations": MAX_ITERATIONS, "run_scorers_in_docker": False, "random_candidate_ratio": 0.0,
                "return_all_candidates": False, "stop_on_analyzer_decision": False,
                "budget": {"max_oracle_evals": job["budget"]}, **task.loop_overrides}
        if job["arm"] != "A":
            validation = dict(GATES[job["gate"]], seeds=[1000 * (seed + 1), 1000 * (seed + 1) + 1], trial_optimizer_overrides={},
                              seed_key="seed", cost_multiplier=float(job["cost"]))
            judge = {"type": "random", "seed": seed} if job["arm"] == "RND" else {"type": "none"}
            loop["meta_controller"] = {"enabled": True, "task_id": task.task_id, "seed": seed, "judge": judge,
                                       "validator": task.validator, "validation": validation, "max_ops_per_change": 1}
        orch = OptimizationOrchestrator(FrameworkConfig(loop_config=loop, modules=modules), run_name="valreal", run_id="valreal")
        mc = orch.meta_controller
        sim = None
        if job["arm"] != "A":
            mc.validator = make_realism_validator(task.task_id, job["variant"], seed=job.get("noise_seed", seed))
            if job["arm"] == "SIM":
                sim = mocks.SimulatedJudge(job["fix"], job["wrong"], seed=seed)
                sim.controller = mc
                mc.set_judge(sim)
        population = Population(candidates=[Candidate(representation=v) for v in initial_population_vectors(task.dim, 32, seed)])
        t0 = time.time()
        asyncio.run(orch.run(high_level_goal=task.goal, context_information=task.context,
                             serializer_name="vector_serializer", initial_population=population))
        test = get_numeric_validator(task.validator).evaluate([c.representation for c in orch.current_population.candidates], split="test")
        labels = {p["record_index"]: p["label"] for p in (sim.proposals if sim else [])}
        decisions = []
        for i, r in enumerate(mc.records if mc else []):
            v = r.get("validation") or {}
            exact_delta = None
            if v.get("delta") is not None:   # shadow: the exact validator on the same final-stage populations (diagnostic only)
                details = v.get("details") or {}
                exact = {side: [d.get("exact_validation_metric", d.get("metric")) for d in details.get(side, [])]
                         for side in ("baseline", "candidate")}
                if job["variant"] == "oracle":
                    exact_delta = v["delta"]
                elif all(exact.values()) and None not in exact["baseline"] + exact["candidate"]:
                    exact_delta = float(np.mean(exact["candidate"]) - np.mean(exact["baseline"]))
            decisions.append({
                "iteration": r["iteration"], "label": labels.get(i), "target": (r.get("decision") or {}).get("intervention_target"),
                "change_id": r.get("change_id"), "outcome": r["outcome"], "reason": r["reason"][:140],
                "stages": len(v.get("stages", [])) or (1 if v.get("delta") is not None else 0), "delta": v.get("delta"),
                "exact_delta": exact_delta,
                "evals": (r["costs"].get("candidate", {}).get("oracle_evals") or 0) + (r["costs"].get("validation", {}).get("oracle_evals") or 0),
            })
        used = orch.budget_guard.usage()["oracle_evals"] if orch.budget_guard else None
        return {**{k: job[k] for k in KEY},
                "test_metric": test.metric, "iterations_completed": orch.current_iteration,
                "termination_reason": orch.result.termination_reason if orch.result else None,
                "evals_used": used, "evals_main": orch.optimizer.num_evaluations,
                "evals_trials": mc.trial_evals if mc else 0, "evals_validation_budget_units": mc.validation_evals if mc else 0,
                "evals_validation_raw": mc.validation_evals_raw if mc else 0, "decisions": decisions,
                "seconds": round(time.time() - t0, 1)}
    finally:
        os.chdir(ROOT)
        shutil.rmtree(workdir, ignore_errors=True)


def _safe(fn, job):
    try:
        return fn(job)
    except Exception as e:  # recorded, never silently dropped
        import traceback
        return {**{k: job.get(k) for k in ("kind", "label") + KEY},
                "error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()[-2000:]}


def run_gt(job):
    return _safe(_run_job, job)


def run_e2e(job):
    return _safe(_run_e2e, job)


def gt_jobs(tmp_root, tasks, seeds):
    jobs = []
    for condition in CONDITIONS:
        for task in tasks:
            if task not in EXPLOITS:
                continue
            label, probe = exploit_probe(condition, task)
            for seed in seeds:
                base = {"condition": condition, "task": task, "seed": seed, "tmp_root": tmp_root, "kind": "ground_truth",
                        "gate": OLD_GATE, "gate_name": "-", "iterations": GT_ITERS}
                jobs.append(dict(base, label="control:no_change", probe=None, force_accept=False))
                jobs.append(dict(base, label=label, probe=probe, force_accept=True))
    return jobs


def noise_seed(condition, task, seed, stream):
    """'shared' (pre-registered run): the noise stream depends on the seed only, so it is identical across tasks and
    configs. 'independent' (amendment 3 robustness check): one stream per (task, condition, seed)."""
    if stream == "shared":
        return seed
    import zlib
    return zlib.crc32(f"{task}|{condition}|{seed}".encode()) % 1_000_000


def e2e_jobs(tmp_root, tasks, seeds, classes, configs, stream="shared"):
    jobs = []
    for condition in CONDITIONS:
        for task in tasks:
            fix, wrong = judge_menu(condition, task, classes)
            for seed in seeds:
                for arm, variant, cost, gate, budget in configs:
                    jobs.append({"arm": arm, "variant": variant, "cost": cost, "gate": gate, "budget": budget,
                                 "condition": condition, "task": task, "seed": seed, "tmp_root": tmp_root,
                                 "fix": fix, "wrong": wrong, "noise_seed": noise_seed(condition, task, seed, stream)})
    return jobs


def all_configs():
    out = []
    for budget in BUDGETS:
        out.append(("A", "-", "-", "-", budget))
        out += [(arm, v, c, g, budget) for g in GATES for arm in ("SIM", "RND") for v in VARIANTS for c in COSTS]
    return out


def _pool_run(fn, jobs, path, workers):
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool, open(path, "w") as f:
        for i, r in enumerate(pool.map(fn, jobs), 1):
            results.append(r)
            f.write(json.dumps(r) + "\n")
            f.flush()
            if i % 50 == 0 or i == len(jobs):
                print(f"{path.name}: {i}/{len(jobs)} done", flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--smoke", action="store_true", help="offset_scorer, seed 0, initial condition only")
    parser.add_argument("--variants", default=",".join(VARIANTS), help="validator variants to run (A always runs)")
    parser.add_argument("--noise-stream", choices=("shared", "independent"), default="shared")
    parser.add_argument("--out", default=str(ROOT / "exps" / "meta_controller" / "results" / "v5" / "validator_realism"))
    args = parser.parse_args()
    out = Path(args.out + ("_smoke" if args.smoke else ""))
    out.mkdir(parents=True, exist_ok=True)
    tmp_root = tempfile.mkdtemp(prefix="valreal_root_")
    tasks = ["offset_scorer"] if args.smoke else list(PROBES)
    seeds = [0] if args.smoke else SEEDS
    classes = v4_classes()
    t0 = time.time()
    gt = _pool_run(run_gt, gt_jobs(tmp_root, tasks, seeds), out / "gt_runs.jsonl", args.workers)
    variants = set(args.variants.split(","))
    configs = [c for c in all_configs() if c[0] == "A" or c[1] in variants]
    runs = _pool_run(run_e2e, e2e_jobs(tmp_root, tasks, seeds, classes, configs, args.noise_stream), out / "runs.jsonl", args.workers)
    shutil.rmtree(tmp_root, ignore_errors=True)
    print(f"total {time.time() - t0:.0f}s", flush=True)
    summarize(gt, runs, classes, out)


def summarize(gt, runs, classes, out: Path):
    import numpy as np
    from modules.numeric_tasks.tasks import load_success_thresholds

    thresholds = load_success_thresholds()
    errors = [r for r in gt + runs if "error" in r]
    # ---- ground truth of the exploit probes (same protocol and labels as v4)
    classes = dict(classes)
    gt_index = {(r["condition"], r["task"], r["label"], r["seed"]): r for r in gt if "error" not in r}
    exploit_rows = []
    for (condition, task, label, seed) in sorted({k[:3] + (None,) for k in gt_index if k[2].startswith("exploit:")}):
        seeds = sorted(s for (c, t, l, s) in gt_index if (c, t, l) == (condition, task, label))
        effects = [gt_index[(condition, task, label, s)]["test_metric"] - gt_index[(condition, task, "control:no_change", s)]["test_metric"]
                   for s in seeds if (condition, task, "control:no_change", s) in gt_index]
        applied = all(gt_index[(condition, task, label, s)]["outcome"] == "accepted" for s in seeds)
        mean = float(np.mean(effects)) if effects else float("nan")
        cls = "not_applicable" if not applied else "beneficial" if mean > 0.05 else "harmful" if mean < -0.05 else "neutral"
        classes[(condition, task, label)] = cls
        exploit_rows.append({"condition": condition, "task": task, "probe": label, "true_effect_mean": round(mean, 3),
                             "true_effect_per_seed": [round(e, 3) for e in effects], "class": cls})

    ok = [r for r in runs if "error" not in r]
    a_index = {(r["budget"], r["condition"], r["task"], r["seed"]): r for r in ok if r["arm"] == "A"}
    configs = []
    for r in ok:
        key = tuple(r[k] for k in CONFIG)
        if key not in configs:
            configs.append(key)
    rows = []
    for config in configs:
        arm, variant, cost, gate, budget = config
        rs = [r for r in ok if tuple(r[k] for k in CONFIG) == config]
        diffs = [r["test_metric"] - a_index[(r["budget"], r["condition"], r["task"], r["seed"])]["test_metric"]
                 for r in rs if (r["budget"], r["condition"], r["task"], r["seed"]) in a_index]
        accepted = [d for r in rs for d in r["decisions"] if d["outcome"] == "accepted"]
        by_class = {"beneficial": 0, "neutral": 0, "harmful": 0, "unlabeled": 0}
        for r in rs:
            for d in r["decisions"]:
                if d["outcome"] == "accepted":
                    by_class[classes.get((r["condition"], r["task"], d["label"]), "unlabeled") if d["label"] else "unlabeled"] += 1
        fix_cells = [r for r in rs if any((d["label"] or "").startswith("fix:") for d in r["decisions"])]
        fix_accepted = [r for r in fix_cells if any((d["label"] or "").startswith("fix:") and d["outcome"] == "accepted" for d in r["decisions"])]
        exploit_cells = [r for r in rs if any((d["label"] or "").startswith("exploit:") for d in r["decisions"])]
        exploit_accepted = [r for r in exploit_cells if any((d["label"] or "").startswith("exploit:") and d["outcome"] == "accepted"
                                                            for d in r["decisions"])]
        judged = [d for r in rs for d in r["decisions"] if d["delta"] is not None and d["exact_delta"] is not None]
        shadow = {
            "accepted": sum(d["outcome"] == "accepted" for d in judged),
            "accepted_exact_worse": sum(d["outcome"] == "accepted" and d["exact_delta"] < 0 for d in judged),
            "accepted_exact_worse_by_0.02": sum(d["outcome"] == "accepted" and d["exact_delta"] <= -0.02 for d in judged),
            "rejected": sum(d["outcome"] != "accepted" for d in judged),
            "rejected_exact_better_by_0.02": sum(d["outcome"] != "accepted" and d["exact_delta"] >= 0.02 for d in judged),
        }
        val_share = [r["evals_validation_budget_units"] / r["evals_used"] for r in rs if r["evals_used"]]
        ctrl_share = [(r["evals_validation_budget_units"] + r["evals_trials"]) / r["evals_used"] for r in rs if r["evals_used"]]
        rows.append({
            "arm": arm, "variant": variant, "cost": cost, "gate": gate, "budget": budget, "n": len(rs),
            "mean_test": round(float(np.mean([r["test_metric"] for r in rs])), 3),
            "success": sum(r["test_metric"] >= thresholds.get(r["task"], float("inf")) for r in rs),
            "mean_diff_vs_A": round(float(np.mean(diffs)), 3) if diffs else None,
            "cells_worse_than_A_by_0.05": sum(d < -0.05 for d in diffs),
            "cells_better_than_A_by_0.05": sum(d > 0.05 for d in diffs),
            "decisions_validated": sum(d["stages"] > 0 for r in rs for d in r["decisions"]),
            "accepted": len(accepted), "accepted_by_true_class": by_class, "shadow_exact_validator": shadow,
            "fix_accepted_cells": f"{len(fix_accepted)}/{len(fix_cells)}",
            "exploit_accepted_cells": f"{len(exploit_accepted)}/{len(exploit_cells)}",
            "mean_iterations": round(float(np.mean([r["iterations_completed"] for r in rs])), 1),
            "mean_validation_share_of_evals": round(float(np.mean(val_share)), 3) if val_share else 0.0,
            "mean_controller_share_of_evals": round(float(np.mean(ctrl_share)), 3) if ctrl_share else 0.0,
        })
    per_task = {}
    for config in configs:
        for task in sorted({r["task"] for r in ok}):
            for condition in CONDITIONS:
                rs = [r for r in ok if tuple(r[k] for k in CONFIG) == config and (r["task"], r["condition"]) == (task, condition)]
                if rs:
                    per_task["|".join(map(str, config + (task, condition)))] = round(float(np.mean([r["test_metric"] for r in rs])), 3)
    summary = {"note": "OFFLINE, no LLM. SIM = simulated (mock) judge, not an LLM. Test metric = exact validator, test split.",
               "budgets": BUDGETS, "gates": GATES, "errors": len(errors), "exploit_ground_truth": exploit_rows,
               "configs": rows, "per_task_mean_test": per_task}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    lines = ["# v5 validator realism (offline, no LLM; SIM = simulated judge)", "", summary["note"], "",
             f"errors: {len(errors)}", "", "## Ground truth of the bug-exploiting probes (v4 protocol)", "",
             "| condition | task | probe | true effect | class |", "|---|---|---|---|---|"]
    for e in exploit_rows:
        lines.append(f"| {e['condition']} | {e['task']} | {e['probe']} | {e['true_effect_mean']:+.3f} | {e['class']} |")
    lines += ["", "## Arms (60 cells each: 6 tasks x 2 objective conditions x 5 seeds)", "",
              "| budget | gate | arm | validator | cost | mean test | success | diff vs A | worse/better than A (>0.05) | accepted (ben/neu/harm/unlab) | accepted: exact says worse / worse by 0.02 | rejected: exact says better by 0.02 | fix accepted | exploit accepted | iters | validation share | controller share |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        c, sh = r["accepted_by_true_class"], r["shadow_exact_validator"]
        diff = "" if r["mean_diff_vs_A"] is None else f"{r['mean_diff_vs_A']:+.3f}"
        lines.append(f"| {r['budget']} | {r['gate']} | {r['arm']} | {r['variant']} | {r['cost']} | {r['mean_test']:.3f} | {r['success']}/{r['n']} | {diff} | "
                     f"{r['cells_worse_than_A_by_0.05']}/{r['cells_better_than_A_by_0.05']} | "
                     f"{c['beneficial']}/{c['neutral']}/{c['harmful']}/{c['unlabeled']} | "
                     f"{sh['accepted_exact_worse']}/{sh['accepted_exact_worse_by_0.02']} of {sh['accepted']} | "
                     f"{sh['rejected_exact_better_by_0.02']} of {sh['rejected']} | {r['fix_accepted_cells']} | {r['exploit_accepted_cells']} | "
                     f"{r['mean_iterations']} | {r['mean_validation_share_of_evals']:.2f} | {r['mean_controller_share_of_evals']:.2f} |")
    tasks = sorted({r["task"] for r in ok})
    lines += ["", "## Mean test metric per task (both objective conditions pooled per column pair: initial / planner_observed)", "",
              "| budget | gate | arm | validator | cost | " + " | ".join(tasks) + " |", "|---|---|---|---|---|" + "---|" * len(tasks)]
    for config in configs:
        cells = []
        for task in tasks:
            vals = [per_task.get("|".join(map(str, config + (task, c)))) for c in CONDITIONS]
            cells.append(" / ".join("-" if v is None else f"{v:.2f}" for v in vals))
        arm, variant, cost, gate, budget = config
        lines.append(f"| {budget} | {gate} | {arm} | {variant} | {cost} | " + " | ".join(cells) + " |")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
