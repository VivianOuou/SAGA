"""
Independent validators for accept/reject decisions.

A validator is fixed before the run and is independent of the objectives the planner/judge can
change: it recomputes quality from candidate representations and never reads candidate.scores.
Validators expose two disjoint splits:
- "validation": used by the Meta-Controller for accept/reject (the only split it may use)
- "test": reserved for final reporting by the experiment harness; never used for selection
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


VALIDATION_SPLIT = "validation"
TEST_SPLIT = "test"


@dataclass
class ValidationResult:
    metric: float
    n_evals: int
    constraint_violation: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class BaseValidator(ABC):
    name: str = "base"
    higher_is_better: bool = True

    @abstractmethod
    def evaluate(self, representations: List[Any], split: str = VALIDATION_SPLIT) -> ValidationResult:
        """Score a population (given as raw candidate representations) on the requested split."""

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "higher_is_better": self.higher_is_better}


_VALIDATOR_FACTORIES: Dict[str, Callable[[], BaseValidator]] = {}


def register_validator(name: str, factory: Callable[[], BaseValidator]) -> None:
    if name in _VALIDATOR_FACTORIES:
        raise ValueError(f"Validator '{name}' already registered")
    _VALIDATOR_FACTORIES[name] = factory


def get_validator(name: Optional[str]) -> Optional[BaseValidator]:
    if not name or name not in _VALIDATOR_FACTORIES:
        return None
    return _VALIDATOR_FACTORIES[name]()


def list_validators() -> List[str]:
    return sorted(_VALIDATOR_FACTORIES)
