"""
Accepted intervention state and how it is applied to the objectives used by the optimizer.

The state only ever changes through MetaController._commit() after a candidate passed independent
validation. Objective and implementation patches are re-applied after every scorer-creation phase
(keyed by objective name), so the planner/implementer re-proposing an objective does not silently
bring back an old binding or weight.
"""

import copy
import inspect
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.data_models import Objective


MAX_TOTAL_GUIDANCE_CHARS = 2500


@dataclass
class AcceptedState:
    version: int = 0
    planner_guidance: Optional[str] = None
    objective_ops: List[Dict[str, Any]] = field(default_factory=list)
    implementation_patches: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    workflow_params: Dict[str, Any] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not (self.planner_guidance or self.objective_ops or self.implementation_patches or self.workflow_params)

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(asdict(self))


def merge_change(state: AcceptedState, target: str, change) -> AcceptedState:
    """Return a NEW state = state + change (the input state is not modified)."""
    new = copy.deepcopy(state)
    if target == "objective":
        names = {op.name for op in change.ops}
        new.objective_ops = [op for op in new.objective_ops if op["name"] not in names]
        new.objective_ops.extend(op.model_dump(exclude_none=True) for op in change.ops)
    elif target == "planning":
        if change.mode == "append" and new.planner_guidance:
            new.planner_guidance = (new.planner_guidance + "\n" + change.guidance)[-MAX_TOTAL_GUIDANCE_CHARS:]
        else:
            new.planner_guidance = change.guidance
    elif target == "implementation":
        patch = change.model_dump(exclude_none=True)
        patch.pop("objective_name")
        new.implementation_patches[change.objective_name] = patch
    elif target == "optimization_workflow":
        new.workflow_params.update(change.params)
    else:
        raise ValueError(f"cannot merge target '{target}'")
    return new


def _copy_objective(obj: Objective, **updates) -> Objective:
    data = {
        "name": obj.name,
        "description": obj.description,
        "type": obj.type,
        "optimization_direction": obj.optimization_direction,
        "weight": obj.weight,
        "metadata": copy.deepcopy(obj.metadata),
    }
    data.update({k: v for k, v in updates.items() if k != "scorer"})
    new = Objective(**data)
    new.scorer = updates.get("scorer", obj.scorer)
    return new


def make_sanitizing_scorer(inner: Callable, low: float, high: float) -> Callable:
    """Wrap a candidate-wise scorer: non-finite or out-of-range outputs become None (failed)."""

    async def sanitized(*args, force_evaluation: bool = False, **kwargs):
        if inspect.iscoroutinefunction(inner):
            values = await inner(*args, force_evaluation=force_evaluation, **kwargs)
        else:
            values = inner(*args, force_evaluation=force_evaluation, **kwargs)
        out = []
        for v in values:
            if isinstance(v, bool) or v is None:
                out.append(v)
                continue
            try:
                f = float(v)
            except (TypeError, ValueError):
                out.append(None)
                continue
            out.append(f if (math.isfinite(f) and low <= f <= high) else None)
        return out

    sanitized._meta_controller_sanitized = (low, high)
    return sanitized


def apply_state_to_objectives(
    objectives: List[Objective],
    state: AcceptedState,
    scorer_lookup: Callable[[str], Optional[Callable]],
    scorer_metadata: Callable[[str], Optional[Dict[str, Any]]],
) -> Tuple[List[Objective], List[str]]:
    """
    Apply accepted objective ops and implementation patches to a list of objectives.

    The input objectives are not modified. Ops that do not apply (e.g. the objective is absent in
    this iteration) are skipped and reported in the returned notes.
    """
    notes: List[str] = []
    result = list(objectives)

    for op in state.objective_ops:
        name = op["name"]
        idx = next((i for i, o in enumerate(result) if o.name == name), None)
        if op["op"] == "set_weight":
            if idx is None:
                notes.append(f"set_weight({name}) skipped: objective absent")
                continue
            result[idx] = _copy_objective(result[idx], weight=float(op["weight"]))
        elif op["op"] == "drop":
            if idx is None:
                notes.append(f"drop({name}) skipped: objective absent")
                continue
            remaining = [o for i, o in enumerate(result) if i != idx and o.type != "filter"]
            if not remaining:
                notes.append(f"drop({name}) skipped: would leave no optimizable objective")
                continue
            result.pop(idx)
        elif op["op"] == "add_from_registry":
            if idx is not None:
                notes.append(f"add_from_registry({name}) skipped: already present")
                continue
            scorer = scorer_lookup(name)
            meta = scorer_metadata(name) or {}
            if scorer is None:
                notes.append(f"add_from_registry({name}) skipped: scorer not registered")
                continue
            obj_type = meta.get("type", "candidate-wise")
            result.append(Objective(
                name=name,
                description=meta.get("description", ""),
                type=obj_type,
                optimization_direction=None if obj_type == "filter" else op.get("optimization_direction"),
                weight=op.get("weight"),
                scorer=scorer,
                metadata={"added_by": "meta_controller"},
            ))

    for name, patch in state.implementation_patches.items():
        idx = next((i for i, o in enumerate(result) if o.name == name), None)
        if idx is None:
            notes.append(f"implementation patch for {name} skipped: objective absent")
            continue
        obj = result[idx]
        action = patch["action"]
        if action in ("rebind_scorer", "rebuild_scorer"):
            scorer_name = patch["scorer_name"]
            scorer = scorer_lookup(scorer_name)
            if scorer is None:
                notes.append(f"{action}({name}->{scorer_name}) skipped: scorer not registered")
                continue
            metadata = copy.deepcopy(obj.metadata)
            metadata["meta_controller_scorer_binding"] = scorer_name
            result[idx] = _copy_objective(obj, scorer=scorer, metadata=metadata)
        elif action == "sanitize_outputs":
            if obj.scorer is None:
                notes.append(f"sanitize_outputs({name}) skipped: objective has no scorer")
                continue
            low, high = patch["valid_range"]
            metadata = copy.deepcopy(obj.metadata)
            metadata["meta_controller_sanitized_range"] = [low, high]
            result[idx] = _copy_objective(obj, scorer=make_sanitizing_scorer(obj.scorer, low, high), metadata=metadata)

    return result, notes


def patched_objective_names(state: AcceptedState) -> List[str]:
    return sorted(set(state.implementation_patches) | {op["name"] for op in state.objective_ops})
