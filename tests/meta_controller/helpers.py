"""
MOCK / SYNTHETIC test helpers for the Meta-Controller (no API keys, GPU, Docker or network).

Everything here is deterministic and exists only to exercise the real controller logic. Results
produced with these helpers say nothing about whether a real LLM judge improves SAGA.
"""

import importlib
import json
from typing import Any, Dict, List, Optional

from scileo_agent.core.config import FrameworkConfig, ModuleConfig
from scileo_agent.core.data_models import Candidate, Population
from scileo_agent.core.orchestrator import OptimizationOrchestrator
from scileo_agent.core.registry.scorer_registry import ScorerManager, list_scorers

from modules.shared import knowledge_manager, scorer_creator  # noqa: F401  (registers modules)
from modules.numeric_tasks import numeric_ga_optimizer, vector_serializer  # noqa: F401
from modules.numeric_tasks.mocks import (  # noqa: F401
    FAKE_SECRET, FakeLLMClient, MockRulePlanner, MockStatsAnalyzer, ScriptedJudge, ScriptedValidator, decision, no_change,
)
from modules.numeric_tasks.tasks import TASKS, initial_population_vectors
from modules.numeric_tasks.validators import register_numeric_validators

register_numeric_validators()


def register_inprocess_scorers(task_id: str, extra: Optional[Dict[str, Any]] = None) -> List[str]:
    """Register a task's proxy scorers in-process (bypasses MCP subprocesses; same caching semantics)."""
    task = TASKS[task_id]
    base = importlib.import_module(task.mcp_module.replace("/", ".") + ".base")
    init = importlib.import_module(task.mcp_module.replace("/", "."))
    instance = base.Scorer()
    fns = {name: instance.scorers[name]["method"] for name in init.scorers}
    types = {name: init.scorers[name]["type"] for name in init.scorers}
    descriptions = {name: init.scorers[name]["description"] for name in init.scorers}
    for name, (fn, typ, desc) in (extra or {}).items():
        fns[name], types[name], descriptions[name] = fn, typ, desc
    manager = ScorerManager(run_in_docker=False)
    for name, fn in fns.items():
        manager.register_scorer(
            scorer_func=_make_cached_scorer(name, fn, types[name]),
            name=name,
            metadata={"description": descriptions[name], "mcp_module": f"inprocess_{task_id}"},
            type=types[name],
            is_mcp_scorer=True,
            mcp_module_name=f"inprocess_{task_id}",
        )
    return sorted(fns)


def _make_cached_scorer(name, fn, scorer_type):
    async def wrapper(population, force_evaluation: bool = False, **kwargs):
        candidates = population.candidates if isinstance(population, Population) else population
        todo = [i for i, c in enumerate(candidates) if force_evaluation or name not in c.scores]
        fresh = fn([json.dumps(candidates[i].representation) for i in todo]) if todo else []
        if scorer_type == "filter":
            fresh = [None if v is None else bool(v) for v in fresh]
        result = [candidates[i].scores.get(name) for i in range(len(candidates))]
        for i, v in zip(todo, fresh):
            result[i] = v
        return result

    wrapper.calls = 0
    return wrapper


def module_configs(task_id: str, planner_objectives: Dict[str, str], ga: Optional[Dict[str, Any]] = None,
                   analyzer: Optional[Dict[str, Any]] = None) -> Dict[str, ModuleConfig]:
    task = TASKS[task_id]
    ga_cfg = {"dim": task.dim, "pop_size": 16, "generations": 3, "seed": 0}
    ga_cfg.update(ga or {})
    specs = {
        "planner": ("planner", "mock_rule_planner", {"objectives": planner_objectives}),
        "scorer_creator": ("scorer_creator", "general_scorer_creator",
                           {"enable_llm_scorer_creation": False, "enable_llm_matching": False}),
        "optimizer": ("optimizer", "numeric_ga_optimizer", ga_cfg),
        "analyzer": ("analyzer", "mock_stats_analyzer", analyzer or {}),
        "knowledge_manager": ("knowledge_manager", "basic_knowledge_manager", {}),
    }
    out = {}
    for module_id, (mtype, name, cfg) in specs.items():
        out[module_id] = ModuleConfig(module_id=module_id, module_type=mtype, module_name=name, config=cfg, llm_config=None)
    return out


def make_orchestrator(run_id: str, task_id: str = "spectral_signal", planner_objectives=None, meta: Optional[Dict] = None,
                      budget: Optional[Dict] = None, max_iterations: int = 3, ga=None, analyzer=None,
                      random_candidate_ratio: float = 0.0) -> OptimizationOrchestrator:
    task = TASKS[task_id]
    planner_objectives = planner_objectives or dict(task.initial_objectives)
    loop = {"max_iterations": max_iterations, "run_scorers_in_docker": False, "random_candidate_ratio": random_candidate_ratio,
            "return_all_candidates": False}
    if meta is not None:
        loop["meta_controller"] = meta
    if budget is not None:
        loop["budget"] = budget
    config = FrameworkConfig(loop_config=loop, modules=module_configs(task_id, planner_objectives, ga, analyzer))
    return OptimizationOrchestrator(config, run_name=run_id, run_id=run_id)


def meta_config(task_id: str = "spectral_signal", **overrides) -> Dict[str, Any]:
    cfg = {
        "enabled": True,
        "task_id": task_id,
        "seed": 0,
        "judge": {"type": "none"},
        "validator": TASKS[task_id].validator,
        "validation": {"seeds": [11], "min_improvement": 0.0, "trial_optimizer_overrides": {"generations": 3}},
    }
    cfg.update(overrides)
    return cfg


def initial_population(task_id: str, size: int = 16, seed: int = 0) -> Population:
    return Population(candidates=[Candidate(representation=v) for v in initial_population_vectors(TASKS[task_id].dim, size, seed)])


async def run(orch: OptimizationOrchestrator, task_id: str = "spectral_signal"):
    task = TASKS[task_id]
    return await orch.run(high_level_goal=task.goal, context_information=task.context,
                          serializer_name="vector_serializer", initial_population=initial_population(task_id))


def fingerprint(orch: OptimizationOrchestrator) -> Dict[str, Any]:
    """Everything a rejected candidate must leave untouched."""
    population = orch.current_population
    km = orch.knowledge_manager
    return {
        "planner_history": json.dumps(getattr(orch.planner, "message_history", []), sort_keys=True, default=str),
        "planner_guidance": getattr(orch.planner, "strategy_guidance", None),
        "planner_call_count": orch.planner.call_count,
        "population": json.dumps([[c.id, c.representation, sorted(c.scores.items())] for c in population.candidates], default=str) if population else None,
        "population_stat_cache": json.dumps([population.regular_scores_mean, population.regular_scores_none_count], default=str) if population else None,
        "km_iterations": sorted(km.populations_by_iteration), "km_objectives": {k: [o.name for o in (v or [])] for k, v in km.objectives_by_iteration.items()},
        "km_reports": dict(km.analysis_reports_by_iteration),
        "registry": sorted(list_scorers()),
        "optimizer_params": {k: v["current"] for k, v in orch.optimizer.tunable_params().items()},
        "optimizer_evals": orch.optimizer.num_evaluations,
        "loop_config": json.dumps(orch.config.loop_config, sort_keys=True, default=str),
        "accepted_state": orch.meta_controller.state.to_dict() if orch.meta_controller else None,
    }
