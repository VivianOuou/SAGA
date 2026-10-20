"""
In-process registration of the synthetic tasks' proxy scorers (no MCP subprocess), with the same
per-scorer-name score caching semantics as SAGA's MCP wrapper. Used by offline tests and the offline
gate-calibration study (exps/meta_controller/gate_calibration.py).
"""

import importlib
import json
from typing import Any, Dict, List, Optional

from scileo_agent.core.data_models import Population
from scileo_agent.core.registry.scorer_registry import ScorerManager

from .tasks import TASKS


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
