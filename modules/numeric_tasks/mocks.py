"""
MOCK components for offline tests and offline pipeline checks of the Meta-Controller.

Nothing here calls a model or the network. Outputs produced with these mocks only show that the
pipeline runs; they say nothing about whether a real LLM judge improves SAGA.
"""

import copy
import json
import re
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from scileo_agent.core.data_models import Objective
from scileo_agent.core.modules import AnalyzerModule, PlannerModule
from scileo_agent.core.modules.base import BaseModule
from scileo_agent.core.registry.module_registry import register_module
from scileo_agent.meta_controller.judge import BaseJudge, JudgeOutput, extract_decision_json
from scileo_agent.meta_controller.validators import ValidationResult


FAKE_SECRET = "sk-THISISAFAKEKEYFORTESTS1234567890"


class FakeLLMClient:
    """MOCK LLM client: never touches the network. Optional synthetic usage per call."""

    def __init__(self, model: str = "mock/fake-model", tokens_per_call: int = 100, with_usage: bool = True,
                 replies: Optional[List[str]] = None):
        self.replies = list(replies or [])
        self.model = model
        self.tokens_per_call = tokens_per_call
        self.with_usage = with_usage
        self.stats: Dict[str, Dict[str, Any]] = {}
        self.responses: List[Dict[str, Any]] = []
        self.config = SimpleNamespace(provider="mock", model=model, max_retries=0, extra_args={"api_key": FAKE_SECRET})

    def record(self, messages, content: str) -> Dict[str, Any]:
        s = self.stats.setdefault(self.model, {"call_count": 0, "total_tokens": 0, "input_tokens": 0,
                                               "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                                               "output_tokens": 0, "cost": 0.0})
        s["call_count"] += 1
        usage = None
        if self.with_usage:
            s["total_tokens"] += self.tokens_per_call
            s["input_tokens"] += self.tokens_per_call // 2
            s["output_tokens"] += self.tokens_per_call - self.tokens_per_call // 2
            usage = {"total_tokens": self.tokens_per_call}
        self.responses.append({"usage": usage, "messages": copy.deepcopy(messages), "content": content, "model_name": self.model})
        return {"content": content, "total_tokens": self.tokens_per_call if self.with_usage else None}

    async def call_async(self, messages, **kwargs):
        return self.record(messages, self.replies.pop(0) if self.replies else "mock")

    def call(self, messages, **kwargs):
        return self.record(messages, "mock")

    def get_stats(self):
        return copy.deepcopy(self.stats)


class ScriptedJudge(BaseJudge):
    """MOCK judge: returns pre-scripted decisions in order (dicts, raw strings or Exceptions)."""

    judge_type = "scripted_mock"

    def __init__(self, decisions: List[Any], client: Optional[FakeLLMClient] = None):
        self.decisions = list(decisions)
        self.client = client or FakeLLMClient(model="mock/judge", tokens_per_call=50)
        self.calls = 0
        self.contexts: List[Dict[str, Any]] = []

    @property
    def llm_clients(self):
        return [self.client]

    def describe(self):
        return {"judge_type": self.judge_type, "model_name": "mock/judge", "note": "MOCK - scripted decisions"}

    async def decide(self, context):
        self.calls += 1
        self.contexts.append(context)
        item = self.decisions.pop(0) if self.decisions else no_change()
        self.client.record([{"role": "user", "content": "judge"}], "scripted")
        if isinstance(item, Exception):
            return JudgeOutput(error=f"judge_call_failed: {type(item).__name__}: {item}", attempts=1)
        if isinstance(item, str):
            raw, err = extract_decision_json(item)
            return JudgeOutput(raw=raw, raw_text=item, error=None if raw is not None else f"judge_output_unparseable: {err}", attempts=1)
        return JudgeOutput(raw=item, raw_text=json.dumps(item), attempts=1)


class SimulatedJudge(BaseJudge):
    """
    SIMULATED judge (MOCK, no LLM) for the offline validator-realism study (PREREG_v5.md).

    Menu = one designated fix plus wrong / bug-exploiting changes, each (target, change). Per call:
      fix not yet accepted -> the fix with probability p_fix, otherwise a uniformly chosen wrong change
      fix accepted         -> no_change with probability p_no_change_after_fix, otherwise a wrong change
    Wrong changes that were already accepted are not proposed again. Its proposal distribution is an
    assumption of the study, not a model of any real LLM judge.
    """

    judge_type = "simulated_mock"

    def __init__(self, fix, wrong: Dict[str, Any], seed: int = 0, p_fix: float = 0.6, p_no_change_after_fix: float = 0.5,
                 client: Optional[FakeLLMClient] = None):
        import random as _random

        self.fix_label, self.fix = fix
        self.wrong = dict(wrong)
        self.p_fix = p_fix
        self.p_no_change_after_fix = p_no_change_after_fix
        self.rng = _random.Random(7007 + seed)
        self.client = client or FakeLLMClient(model="mock/simulated-judge", tokens_per_call=50)
        self.controller = None          # set by the harness; used only to read outcomes of earlier proposals
        self.proposals: List[Dict[str, Any]] = []   # {"label", "record_index"}

    @property
    def llm_clients(self):
        return [self.client]

    def describe(self):
        return {"judge_type": self.judge_type, "model_name": "mock/simulated-judge", "p_fix": self.p_fix,
                "p_no_change_after_fix": self.p_no_change_after_fix, "note": "MOCK - simulated proposal distribution"}

    def _accepted_labels(self):
        records = self.controller.records if self.controller is not None else []
        return {p["label"] for p in self.proposals
                if p["record_index"] < len(records) and records[p["record_index"]]["outcome"] == "accepted"}

    def _pick(self):
        accepted = self._accepted_labels()
        wrong = [label for label in self.wrong if label not in accepted]
        if self.fix_label not in accepted:
            if self.rng.random() < self.p_fix or not wrong:
                return self.fix_label, self.fix
        elif self.rng.random() < self.p_no_change_after_fix or not wrong:
            return "no_change", ("no_change", None)
        label = self.rng.choice(wrong)
        return label, self.wrong[label]

    async def decide(self, context):
        label, (target, change) = self._pick()
        index = len(self.controller.records) if self.controller is not None else -1
        self.proposals.append({"label": label, "record_index": index, "iteration": context.get("iteration")})
        self.client.record([{"role": "user", "content": "judge"}], "simulated")
        raw = decision(target, change)
        return JudgeOutput(raw=raw, raw_text=json.dumps(raw), attempts=1)


class ScriptedValidator:
    """MOCK validator: returns scripted metrics in call order (baseline seeds first, then candidate seeds)."""

    name = "scripted_validator_mock"
    higher_is_better = True

    def __init__(self, metrics: List[float]):
        self.metrics = list(metrics)
        self.calls = 0

    def evaluate(self, representations, split="validation"):
        assert split == "validation", "the controller must only use the validation split"
        self.calls += 1
        return ValidationResult(metric=self.metrics.pop(0), n_evals=len(representations), details={"mock": True})

    def describe(self):
        return {"name": self.name, "note": "MOCK - scripted metrics"}


def decision(target: str, change: Optional[Dict[str, Any]], failure_location: str = "unknown", **extra) -> Dict[str, Any]:
    d = {
        "failure_location": failure_location,
        "root_cause_hypothesis": "MOCK hypothesis",
        "intervention_target": target,
        "rationale": "MOCK rationale citing the analyzer report",
        "proposed_change": change,
        "expected_benefit": "MOCK expected benefit (hypothesis)",
        "validation_plan": "MOCK validation plan",
    }
    d.update(extra)
    return d


def no_change() -> Dict[str, Any]:
    return decision("no_change", None, failure_location="none")


@register_module("mock_rule_planner", "0.0.1")
class MockRulePlanner(PlannerModule):
    """
    MOCK planner (no LLM): iteration 1 -> configured objectives; later iterations -> the same set,
    edited by strategy guidance tokens `ADD:<name>:<maximize|minimize|filter>` and `REMOVE:<name>`.
    """

    def __init__(self, module_id, config=None, llm_config=None):
        BaseModule.__init__(self, module_id, config, None)
        self.llm_client = FakeLLMClient(model="mock/planner", tokens_per_call=200)
        self.support_filter = bool(self.config.get("support_filter", False))
        self.message_history: List[Dict[str, str]] = []
        self.objective_planning_response_dicts: Dict[int, Any] = {}
        self.strategy_guidance: Optional[str] = None
        self.seen_guidance: List[Optional[str]] = []

    def set_strategy_guidance(self, guidance):
        self.strategy_guidance = guidance

    async def plan_objectives(self, *args, **kwargs):
        raise NotImplementedError

    async def _process(self, iteration_number, high_level_goal, context_information=None, initial_objectives=None,
                       analysis_report=None, mode="normal", additional_information=None):
        await self.llm_client.call_async([{"role": "user", "content": f"plan iteration {iteration_number}"}])
        self.message_history.append({"role": "user", "content": f"iteration {iteration_number} guidance={self.strategy_guidance}"})
        self.seen_guidance.append(self.strategy_guidance)
        spec = dict(self.config["objectives"])
        guidance = self.strategy_guidance or ""
        for name, direction in re.findall(r"ADD:(\w+):(maximize|minimize|filter)", guidance):
            spec[name] = direction
        for name in re.findall(r"REMOVE:(\w+)", guidance):
            spec.pop(name, None)
        objectives = []
        for name, value in spec.items():
            # value: "maximize" | "minimize" | "filter", or {"direction": ..., "weight": ...}
            direction = value["direction"] if isinstance(value, dict) else value
            weight = value.get("weight") if isinstance(value, dict) else None
            is_filter = direction == "filter"
            objectives.append(Objective(name=name, description=f"mock objective {name}",
                                        type="filter" if is_filter else "candidate-wise",
                                        optimization_direction=None if is_filter else direction, weight=weight))
        self.objective_planning_response_dicts[iteration_number] = {"mock": True}
        return {"objectives": objectives, "objective_planning_response_dict": {"mock": True}}


@register_module("mock_stats_analyzer", "0.0.1")
class MockStatsAnalyzer(AnalyzerModule):
    """MOCK analyzer (no LLM): reports objective statistics; never asks to stop unless configured."""

    def __init__(self, module_id, config=None, llm_config=None):
        BaseModule.__init__(self, module_id, config, None)
        self.llm_client = FakeLLMClient(model="mock/analyzer", tokens_per_call=300)

    async def analyze(self, iteration_number, high_level_goal, context_information, current_population,
                      current_objectives, serializer_name, historical_info=None, random_replacement_info=None):
        await self.llm_client.call_async([{"role": "user", "content": "analyze"}])
        await current_population.evaluate(current_objectives)
        lines = ["MOCK ANALYSIS REPORT"]
        for obj in current_objectives:
            vals = [c.scores.get(obj.name) for c in current_population.candidates]
            ok = [float(v) for v in vals if v is not None and not isinstance(v, bool)]
            lines.append(f"{obj.name}: n_ok={len(ok)} none={sum(v is None for v in vals)} max={max(ok) if ok else None}")
        stop_at = self.config.get("stop_at_iteration")
        return {"analysis_report": "\n".join(lines), "should_stop": stop_at is not None and iteration_number >= stop_at,
                "reasoning": "mock"}
