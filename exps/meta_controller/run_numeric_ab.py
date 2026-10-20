"""
Run ONE arm of the numeric-task A/B pilot for the Meta-Controller.

    A = Meta-Controller disabled (original SAGA loop)                + budget caps
    B = Meta-Controller enabled with the plain LLM Judge              + the same budget caps
    C = Meta-Controller enabled with the random-target control judge + the same budget caps (v2)

Both arms share task, seed, initial population/objectives, modules, models, budget caps, trial
quota and timeout. The Judge, candidate trials and independent validation of arm B are charged to
the same caps. The test split is only used here, after the run, for reporting.

Examples (repository root, saga env):
    python exps/meta_controller/run_numeric_ab.py --task spectral_signal --seed 0 --arm B
    python exps/meta_controller/run_numeric_ab.py --task spectral_signal --seed 0 --arm B --offline-mock
        (MOCK planner/analyzer/judge, no API key needed: checks the pipeline only, results are not evidence)
"""

import argparse
import asyncio
import json
import os
import random
import shutil
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
# SAGA starts MCP scorer servers as `python -m ...`; make sure that resolves to THIS interpreter's env.
_ENV_BIN = os.path.dirname(sys.executable)
if os.path.realpath(shutil.which("python") or "") != os.path.realpath(os.path.join(_ENV_BIN, "python")):
    os.environ["PATH"] = _ENV_BIN + os.pathsep + os.environ.get("PATH", "")
for var in ("NO_PROXY", "no_proxy"):  # MCP scorer servers are reached on localhost
    hosts = [h for h in os.environ.get(var, "").split(",") if h]
    os.environ[var] = ",".join(hosts + [h for h in ("localhost", "127.0.0.1", "::1") if h not in hosts])

from scileo_agent.core.config import FrameworkConfig, LLMConfig, ModuleConfig  # noqa: E402
from scileo_agent.core.data_models import Candidate, Objective, Population  # noqa: E402
from scileo_agent.core.orchestrator import OptimizationOrchestrator  # noqa: E402
from scileo_agent.core.registry import McpScorerManager, ScorerManager, get_scorer, get_scorer_metadata, list_scorers, register_mcp_module  # noqa: E402
from scileo_agent.meta_controller.decision_log import redact  # noqa: E402
from scileo_agent.utils.logging import setup_logging  # noqa: E402

from modules.shared import analyzer, knowledge_manager, planner, scorer_creator  # noqa: E402,F401
from modules.numeric_tasks import mocks, numeric_ga_optimizer, vector_serializer  # noqa: E402,F401
from modules.numeric_tasks.tasks import TASKS, initial_population_vectors, load_success_thresholds, scorer_catalog_text  # noqa: E402
from modules.numeric_tasks.validators import get_numeric_validator, register_numeric_validators  # noqa: E402

DEFAULT_CONFIG = ROOT / "exps" / "meta_controller" / "ab_config.yaml"
GRID_INDEX = {(t, s, a): i for i, (t, s, a) in enumerate(
    (t, s, a) for t in ("robust_design", "constrained_yield", "spectral_signal", "stagnant_search", "overflow_scorer",
                        "noisy_search") for s in range(10) for a in ("A", "B", "C"))}

# MOCK decisions used only with --offline-mock (one plausible proposal per task, then no_change).
MOCK_DECISIONS = {
    "robust_design": [mocks.decision("objective", {"ops": [
        {"op": "add_from_registry", "name": "robust_performance_mc", "optimization_direction": "maximize", "weight": 2.0}]},
        failure_location="objective")],
    "constrained_yield": [mocks.decision("planning", {"guidance": "Always include the hard budget filter: ADD:within_cost_budget:filter"},
                                         failure_location="objective")],
    "spectral_signal": [mocks.decision("implementation", {"objective_name": "smoothness", "action": "rebind_scorer",
                                                          "scorer_name": "smoothness_v2"}, failure_location="implementation")],
    "stagnant_search": [mocks.decision("optimization_workflow", {"params": {"mutation_sigma": 0.08}},
                                       failure_location="optimization_workflow")],
    "overflow_scorer": [mocks.decision("implementation", {"objective_name": "quality_score", "action": "sanitize_outputs",
                                                          "valid_range": [0, 1]}, failure_location="implementation")],
    "noisy_search": [mocks.decision("optimization_workflow", {"params": {"mutation_sigma": 0.05}},
                                    failure_location="optimization_workflow")],
}


def llm(cfg, model_key):
    return LLMConfig(models_file=cfg["models_file"], credentials_file=cfg["credentials_file"], model_name=cfg["models"][model_key])


def build_config(cfg, task, seed, arm, run_id, offline_mock):
    planner_objectives = {name: (direction or "filter") for name, direction in task.initial_objectives.items()}
    if offline_mock:
        planner_module = ModuleConfig(module_id="planner", module_type="planner", module_name="mock_rule_planner",
                                      config={"objectives": planner_objectives, "support_filter": True}, llm_config=None)
        analyzer_module = ModuleConfig(module_id="analyzer", module_type="analyzer", module_name="mock_stats_analyzer",
                                       config={}, llm_config=None)
        creator_cfg = {"enable_llm_scorer_creation": False, "enable_llm_matching": False}
        creator_llm = None
    else:
        planner_module = ModuleConfig(module_id="planner", module_type="planner", module_name="general_planner",
                                      config=dict(cfg["planner"], enable_human_feedback=False), llm_config=llm(cfg, "planner"))
        analyzer_module = ModuleConfig(module_id="analyzer", module_type="analyzer", module_name="basic_analyzer", config={
            "enable_candidate_analysis": False,  # needs Claude Code + Docker (not available here)
            "candidate_analyzer_enable_domain_tools": False,
            "enable_refusal_detection": True,
            "refusal_detection_model_name": cfg["models"]["refusal_detection"],
            "enable_human_feedback": False,
            "population_save_dir": f"runs/{run_id}/populations_for_analysis",
        }, llm_config=llm(cfg, "analyzer"))
        creator_cfg = {"enable_llm_scorer_creation": False,  # coding agent needs Claude Code + Docker
                       "enable_name_matching": True, "enable_llm_matching": True,
                       "max_parallel_llm_matching": 2, "coding_workspace_path": f"runs/{run_id}/coding_workspace",
                       "generated_scorer_library_path": f"runs/{run_id}/generated_scorers"}
        creator_llm = llm(cfg, "scorer_matching")

    modules = {
        "planner": planner_module,
        "scorer_creator": ModuleConfig(module_id="scorer_creator", module_type="scorer_creator", module_name="general_scorer_creator",
                                       config=creator_cfg, llm_config=creator_llm),
        "optimizer": ModuleConfig(module_id="optimizer", module_type="optimizer", module_name="numeric_ga_optimizer",
                                  config=dict(cfg["optimizer"], **task.optimizer_overrides, dim=task.dim, seed=seed), llm_config=None),
        "analyzer": analyzer_module,
        "knowledge_manager": ModuleConfig(module_id="knowledge_manager", module_type="knowledge_manager",
                                          module_name="basic_knowledge_manager", config={}, llm_config=None),
    }
    loop = {
        "max_iterations": cfg["loop"]["max_iterations"],
        "random_candidate_ratio": cfg["loop"].get("random_candidate_ratio", 0.0),
        "max_objective_planning_retries": cfg["loop"].get("max_objective_planning_retries", 3),
        "return_all_candidates": True,
        "run_scorers_in_docker": False,
        "budget": dict(cfg["budget"]),
        "stop_on_analyzer_decision": cfg["loop"].get("stop_on_analyzer_decision", True),
    }
    loop.update(task.loop_overrides)
    if arm in ("B", "C"):
        mc = cfg["meta_controller"]
        loop["meta_controller"] = {
            "enabled": True,
            "task_id": task.task_id,
            "seed": seed,
            "judge": ({"type": "random", "seed": seed} if arm == "C" else {"type": "none"} if offline_mock else {
                "type": "llm", "model_name": cfg["models"]["judge"], "models_file": cfg["models_file"],
                "credentials_file": cfg["credentials_file"], "max_parse_retries": mc.get("max_parse_retries", 1)}),
            "max_ops_per_change": mc.get("max_ops_per_change"),
            "validator": task.validator,
            "validation": {
                "seeds": [1000 * (seed + 1) + k for k in range(mc["validation"]["n_seeds"])],
                "min_improvement": mc["validation"]["min_improvement"],
                "trial_optimizer_overrides": mc["validation"]["trial_optimizer_overrides"],
                "seed_key": "seed",
            },
            "estimates": mc.get("estimates", {}),
        }
    return FrameworkConfig(loop_config=loop, modules=modules)


async def run_arm(args, cfg):
    task = TASKS[args.task]
    mode = "offline_mock" if args.offline_mock else "real_llm"
    run_id = f"ab-{mode}-{args.task}-s{args.seed}-{args.arm}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    random.seed(args.seed)
    np.random.seed(args.seed)
    setup_logging(level=args.log_level)
    register_numeric_validators()

    ScorerManager(run_in_docker=False).set_run_in_docker(False)
    # Give each grid cell its own port range so parallel runs never reach each other's scorer servers.
    # Stay in 20000-31999: below the Linux ephemeral range (32768-65535 here) and below 65535.
    McpScorerManager(run_in_docker=False)._next_port = args.port_base or (20000 + 150 * (GRID_INDEX.get((args.task, args.seed, args.arm), 0) % 80))
    if list_scorers():
        raise RuntimeError(f"unexpected pre-registered scorers: {list_scorers()}")
    register_mcp_module(task.mcp_module, serializer_name="vector_serializer")

    initial_objectives = []
    for name, direction in task.initial_objectives.items():
        meta = get_scorer_metadata(name)
        initial_objectives.append(Objective(name=name, description=meta["description"], type=meta["type"],
                                            scorer=get_scorer(name), optimization_direction=direction))
    pop_size = cfg["optimizer"]["pop_size"]
    population = Population(candidates=[Candidate(representation=v) for v in initial_population_vectors(task.dim, pop_size, args.seed)])
    context = task.context + "\n\n" + scorer_catalog_text(list_scorers(), get_scorer_metadata)

    config = build_config(cfg, task, args.seed, args.arm, run_id, args.offline_mock)
    orch = OptimizationOrchestrator(config, run_name=run_id, run_id=run_id)
    if args.arm == "B" and args.offline_mock:
        orch.meta_controller.set_judge(mocks.ScriptedJudge(list(MOCK_DECISIONS[args.task])))

    started = time.monotonic()
    status, error = "completed", None
    try:
        await asyncio.wait_for(
            orch.run(high_level_goal=task.goal, context_information=context, serializer_name="vector_serializer",
                     initial_objectives=initial_objectives, initial_population=population),
            timeout=cfg["timeout_s"],
        )
        status = orch.result.status
    except asyncio.TimeoutError:
        status, error = "timeout", f"hard timeout after {cfg['timeout_s']} s"
    except Exception as e:
        status, error = "failed", redact(f"{type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        try:
            ScorerManager().stop_all_mcp_servers()
        except Exception:
            pass
    wall = time.monotonic() - started

    validator = get_numeric_validator(task.validator)
    final = orch.current_population
    reps = [c.representation for c in final.candidates] if final else []
    test = validator.evaluate(reps, split="test") if reps else None
    val = validator.evaluate(reps, split="validation") if reps else None
    threshold = load_success_thresholds().get(args.task)
    api_stats = {}
    stats_file = orch.output_dir / "api_usage_statistics.json"
    if stats_file.exists():
        api_stats = json.loads(stats_file.read_text())
    controller_summary = orch.meta_controller.summary() if orch.meta_controller else None
    budget = orch.budget_guard.report() if orch.budget_guard else None

    result = {
        "mode": mode,
        "evidence_note": ("REAL LLM calls on SYNTHETIC numeric tasks" if mode == "real_llm"
                          else "MOCK planner/analyzer/judge: pipeline check only, not evidence"),
        "task": args.task, "seed": args.seed, "arm": args.arm,
        "arm_definition": {"A": "A: controller disabled", "B": "B: controller enabled (plain LLM judge)",
                           "C": "C: controller enabled (random-target control judge, no LLM)"}[args.arm],
        "suite": task.suite, "best_target": task.best_target,
        "run_id": run_id, "run_dir": str(orch.run_dir),
        "status": status, "error": error,
        "termination_reason": orch.result.termination_reason,
        "iterations_completed": orch.current_iteration,
        "models": cfg["models"] if mode == "real_llm" else "mock",
        "success_threshold": threshold,
        "success": (test is not None and threshold is not None and test.metric >= threshold),
        "test_metric": test.metric if test else None,
        "test_details": test.details if test else None,
        "final_validation_metric_reference_only": val.metric if val else None,
        "llm_calls": (budget or {}).get("used", {}).get("llm_calls"),
        "total_tokens": (budget or {}).get("used", {}).get("total_tokens"),
        "total_tokens_observed": (budget or {}).get("used", {}).get("total_tokens_observed"),
        "cost_usd": (budget or {}).get("used", {}).get("cost_usd"),
        "oracle_evals": (budget or {}).get("used", {}).get("oracle_evals"),
        "wall_time_s": round(wall, 1),
        "budget": budget,
        "api_usage_total": api_stats.get("total"),
        "meta_controller": controller_summary,
        "config": {k: cfg[k] for k in ("loop", "budget", "optimizer", "meta_controller", "timeout_s")},
        "task_overrides": {"optimizer": task.optimizer_overrides, "loop": task.loop_overrides},
    }
    out = orch.output_dir / "ab_result.json"
    out.write_text(json.dumps(result, indent=2, default=str))
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"{mode}__{args.task}__s{args.seed}__{args.arm}.json").write_text(json.dumps(result, indent=2, default=str))
    decisions = orch.output_dir / "meta_controller_decisions.jsonl"
    if decisions.exists():
        (results_dir / f"{mode}__{args.task}__s{args.seed}__{args.arm}.decisions.jsonl").write_text(decisions.read_text())
    print(json.dumps({k: result[k] for k in ("mode", "task", "seed", "arm", "status", "termination_reason",
                                             "success", "test_metric", "llm_calls", "total_tokens", "oracle_evals", "wall_time_s")}))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", required=True, choices=sorted(TASKS))
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--arm", required=True, choices=["A", "B", "C"])
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--offline-mock", action="store_true", help="MOCK planner/analyzer/judge (no API key); pipeline check only")
    parser.add_argument("--results-dir", default=None, help="default: exps/meta_controller/results[/<config results_subdir>]")
    parser.add_argument("--port-base", type=int, default=None)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    if args.results_dir is None:
        args.results_dir = str(ROOT / "exps" / "meta_controller" / "results" / cfg.get("results_subdir", ""))
    if args.offline_mock:
        args.results_dir = str(Path(args.results_dir) / "offline_mock")
    asyncio.run(run_arm(args, cfg))


if __name__ == "__main__":
    main()
