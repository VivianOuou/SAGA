"""
Intervention-aware Meta-Controller for SAGA (opt-in, disabled by default).

Enable with loop_config["meta_controller"] = {"enabled": True, "validator": "<registered name>", ...}.
See exps/meta_controller/README.md for the design, configuration and experiment entry points.
"""

from .budget import BudgetTracker
from .controller import DEFAULT_CONFIG, LOOP_PARAM_SPECS, MetaController, build_meta_components
from .judge import BaseJudge, JudgeOutput, LLMJudge, RandomTargetJudge
from .schema import FAILURE_LOCATIONS, TARGETS, Decision, parse_decision
from .state import AcceptedState
from .validators import (
    TEST_SPLIT,
    VALIDATION_SPLIT,
    BaseValidator,
    ValidationResult,
    get_validator,
    list_validators,
    register_validator,
)

__all__ = [
    "AcceptedState",
    "BaseJudge",
    "BaseValidator",
    "BudgetTracker",
    "DEFAULT_CONFIG",
    "Decision",
    "FAILURE_LOCATIONS",
    "JudgeOutput",
    "LLMJudge",
    "RandomTargetJudge",
    "LOOP_PARAM_SPECS",
    "MetaController",
    "TARGETS",
    "TEST_SPLIT",
    "VALIDATION_SPLIT",
    "ValidationResult",
    "build_meta_components",
    "get_validator",
    "list_validators",
    "parse_decision",
    "register_validator",
]
