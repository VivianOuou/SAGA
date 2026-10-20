"""
Decision schema for the intervention-aware Meta-Controller.

The Judge must separate three things that are allowed to differ:
- failure_location: where an error / shortfall shows up
- root_cause_hypothesis: a (possibly uncertain) explanation
- intervention_target: what is most worth changing next

Only the *shape* of a decision is validated here (allowed targets, field types, numeric bounds).
Checks that depend on the live run (does an objective / scorer / parameter exist, is the action
supported by the configured modules) are done when the candidate state is built.
"""

import json
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


TARGETS = ("objective", "planning", "implementation", "optimization_workflow", "no_change")
FAILURE_LOCATIONS = ("objective", "planning", "implementation", "optimization_workflow", "analysis", "none", "unknown")

MAX_TEXT_CHARS = 2000
MAX_GUIDANCE_CHARS = 1500


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ObjectiveOp(_Strict):
    """One bounded edit of the objective set used by the optimizer."""

    op: Literal["set_weight", "drop", "add_from_registry"]
    name: str = Field(min_length=1, max_length=128)
    weight: Optional[float] = Field(default=None, ge=0.05, le=20.0)
    optimization_direction: Optional[Literal["maximize", "minimize"]] = None

    @model_validator(mode="after")
    def _check_fields(self):
        if self.op == "set_weight" and self.weight is None:
            raise ValueError("op 'set_weight' requires 'weight'")
        if self.op == "drop" and (self.weight is not None or self.optimization_direction is not None):
            raise ValueError("op 'drop' takes only 'name'")
        return self


class ObjectiveChange(_Strict):
    ops: List[ObjectiveOp] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def _unique_names(self):
        names = [op.name for op in self.ops]
        if len(names) != len(set(names)):
            raise ValueError("each objective may appear in at most one op")
        return self


class PlanningChange(_Strict):
    guidance: str = Field(min_length=20, max_length=MAX_GUIDANCE_CHARS)
    mode: Literal["replace", "append"] = "replace"


class ImplementationChange(_Strict):
    objective_name: str = Field(min_length=1, max_length=128)
    action: Literal["rebind_scorer", "sanitize_outputs", "rebuild_scorer"]
    scorer_name: Optional[str] = Field(default=None, max_length=128)
    valid_range: Optional[Tuple[float, float]] = None
    instructions: Optional[str] = Field(default=None, max_length=MAX_GUIDANCE_CHARS)

    @model_validator(mode="after")
    def _check_action_fields(self):
        if self.action == "rebind_scorer":
            if not self.scorer_name:
                raise ValueError("action 'rebind_scorer' requires 'scorer_name'")
        elif self.action == "sanitize_outputs":
            if self.valid_range is None:
                raise ValueError("action 'sanitize_outputs' requires 'valid_range' [low, high]")
            low, high = self.valid_range
            if not (abs(low) < 1e12 and abs(high) < 1e12 and low < high):
                raise ValueError("'valid_range' must be finite with low < high")
        elif self.action == "rebuild_scorer":
            if not self.instructions or len(self.instructions.strip()) < 20:
                raise ValueError("action 'rebuild_scorer' requires concrete 'instructions'")
        return self


class WorkflowChange(_Strict):
    # Bounds and integrality are checked against the live optimizer's declared parameter specs.
    params: Dict[str, float] = Field(min_length=1, max_length=3)


CHANGE_MODELS = {
    "objective": ObjectiveChange,
    "planning": PlanningChange,
    "implementation": ImplementationChange,
    "optimization_workflow": WorkflowChange,
}


class Decision(_Strict):
    failure_location: Literal[FAILURE_LOCATIONS]
    root_cause_hypothesis: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    intervention_target: Literal[TARGETS]
    rationale: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    proposed_change: Optional[Dict[str, Any]] = None
    expected_benefit: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    validation_plan: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    # Model self-report; NOT calibrated and NOT a probability of measured benefit.
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    # Optional one-sentence assessment per target (requested by judge prompt v2); recorded, not used for acceptance.
    target_assessment: Optional[Dict[str, str]] = None

    @model_validator(mode="after")
    def _check_assessment(self):
        if self.target_assessment is not None:
            unknown = set(self.target_assessment) - set(TARGETS)
            if unknown:
                raise ValueError(f"target_assessment has unknown targets: {sorted(unknown)}")
            if any(len(str(v)) > 600 for v in self.target_assessment.values()):
                raise ValueError("target_assessment entries must be at most 600 characters")
        return self


def _format_validation_error(error: ValidationError) -> str:
    parts = []
    for item in error.errors()[:5]:
        loc = ".".join(str(x) for x in item.get("loc", ()))
        parts.append(f"{loc}: {item.get('msg')}")
    return "; ".join(parts)


def parse_decision(raw: Any) -> Tuple[Optional[Decision], Optional[BaseModel], Optional[str]]:
    """
    Validate a raw Judge output.

    Returns:
        (decision, parsed_change, error). On any error, decision/parsed_change are None and the
        caller must keep the accepted state; it must not reinterpret the output as another action.
    """
    if not isinstance(raw, dict):
        return None, None, f"decision must be a JSON object, got {type(raw).__name__}"
    try:
        decision = Decision.model_validate(raw)
    except ValidationError as e:
        return None, None, "schema: " + _format_validation_error(e)

    target = decision.intervention_target
    if target == "no_change":
        if decision.proposed_change not in (None, {}):
            return None, None, "no_change must not carry a proposed_change"
        return decision, None, None

    if not isinstance(decision.proposed_change, dict):
        return None, None, f"target '{target}' requires an object 'proposed_change'"
    try:
        change = CHANGE_MODELS[target].model_validate(decision.proposed_change)
    except ValidationError as e:
        return None, None, f"proposed_change for '{target}': " + _format_validation_error(e)
    return decision, change, None


def change_fingerprint(target: str, change: Optional[BaseModel]) -> Optional[str]:
    """Stable identifier of a proposed change (sha256 over canonical JSON)."""
    import hashlib

    if change is None:
        return None
    payload = json.dumps({"target": target, "change": change.model_dump()}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
