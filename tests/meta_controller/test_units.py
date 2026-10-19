"""Unit tests (MOCK clients only): decision schema, LLMJudge parsing, cost accounting, redaction."""

import asyncio
import json

from scileo_agent.meta_controller.budget import BudgetTracker
from scileo_agent.meta_controller.decision_log import DecisionLog, redact
from scileo_agent.meta_controller.judge import LLMJudge
from scileo_agent.meta_controller.schema import parse_decision

from tests.meta_controller.helpers import FAKE_SECRET, FakeLLMClient, decision, no_change


def test_failure_location_and_target_may_differ():
    d, change, err = parse_decision(decision("planning", {"guidance": "Always pair objective X with its verified implementation."},
                                             failure_location="implementation"))
    assert err is None
    assert d.failure_location == "implementation" and d.intervention_target == "planning"


def test_schema_rejects_unknown_target_bad_params_and_out_of_range():
    bad = [
        decision("architecture_search", {"x": 1}),                                                # unknown target
        decision("objective", {"ops": [{"op": "set_weight", "name": "a", "weight": 100.0}]}),   # out of range
        decision("objective", {"ops": [{"op": "set_weight", "name": "a"}]}),                      # missing weight
        decision("objective", {"ops": [{"op": "explode", "name": "a"}]}),                         # unknown op
        decision("objective", {"ops": []}),                                                       # empty
        decision("implementation", {"objective_name": "a", "action": "rebind_scorer"}),           # missing scorer
        decision("implementation", {"objective_name": "a", "action": "sanitize_outputs", "valid_range": [1, 0]}),
        decision("optimization_workflow", {"params": {"a": 1, "b": 2, "c": 3, "d": 4}}),          # too many params
        decision("planning", {"guidance": "short"}),                                              # too short
        decision("planning", {"guidance": "x" * 30, "extra_field": 1}),                           # extra field
        dict(no_change(), proposed_change={"ops": []}),                                           # no_change + change
        dict(decision("planning", {"guidance": "x" * 30}), confidence=1.5),                       # confidence > 1
        {"intervention_target": "planning"},                                                      # missing fields
        "not a dict",
    ]
    for raw in bad:
        d, change, err = parse_decision(raw)
        assert d is None and change is None and err, raw


def test_llm_judge_parses_and_retries_with_mock_client():
    good = json.dumps(decision("no_change", None, failure_location="none"))
    client = FakeLLMClient(model="mock/judge", replies=["garbage without tags", f"thinking...<decision>{good}</decision>"])
    judge = LLMJudge(model_name="mock/judge", client=client, max_parse_retries=1)
    out = asyncio.run(judge.decide(_ctx()))
    assert out.error is None and out.raw["intervention_target"] == "no_change" and out.attempts == 2
    described = json.dumps(judge.describe())
    assert FAKE_SECRET not in described and "api_key" not in described


def test_llm_judge_reports_unparseable_and_call_failure():
    client = FakeLLMClient(model="mock/judge", replies=["nope", "still nope"])
    out = asyncio.run(LLMJudge(model_name="m", client=client, max_parse_retries=1).decide(_ctx()))
    assert out.raw is None and out.error.startswith("judge_output_unparseable")

    class Failing(FakeLLMClient):
        async def call_async(self, messages, **kwargs):
            raise RuntimeError(f"AuthenticationError: bad key {FAKE_SECRET}")

    out = asyncio.run(LLMJudge(model_name="m", client=Failing()).decide(_ctx()))
    assert out.error.startswith("judge_call_failed")


def test_missing_usage_is_unknown_not_zero():
    with_usage, without = FakeLLMClient(tokens_per_call=10), FakeLLMClient(with_usage=False)
    tracker = BudgetTracker({"max_llm_calls": 100}, lambda: [with_usage, without, with_usage], lambda: None)
    before = tracker.snapshot()
    with_usage.record([], "a")
    without.record([], "b")
    delta = BudgetTracker.delta(before, tracker.snapshot())
    assert delta["llm_calls"] == 2
    assert delta["total_tokens"] is None and delta["calls_missing_usage"] == 1
    assert delta["total_tokens_observed_lower_bound"] == 10
    assert tracker.usage()["total_tokens"] is None          # shared client counted once, unknown tokens flagged
    assert tracker.usage()["llm_calls"] == 2


def test_budget_caps_and_affordability():
    client = FakeLLMClient(tokens_per_call=100)
    tracker = BudgetTracker({"max_llm_calls": 3, "max_total_tokens": 1000}, lambda: [client], lambda: 5)
    client.record([], "x")
    assert tracker.can_afford({"llm_calls": 2})[0] and not tracker.can_afford({"llm_calls": 3})[0]
    client.record([], "x"), client.record([], "x")
    assert tracker.exhausted()[0]
    assert tracker.remaining()["max_llm_calls"] == 0


def test_redaction_of_secrets(tmp_path):
    record = {"text": f"key={FAKE_SECRET} and AKIAABCDEFGHIJKLMNOP", "api_key": "plain", "nested": [{"token": "abc123456"}]}
    DecisionLog(tmp_path / "log.jsonl").write(record)
    content = (tmp_path / "log.jsonl").read_text()
    assert FAKE_SECRET not in content and "AKIAABCDEFGHIJKLMNOP" not in content and "plain" not in content
    assert redact({"total_tokens": 5})["total_tokens"] == 5


def _ctx():
    return {
        "high_level_goal": "goal", "iteration": 1, "max_iterations": 3, "analysis_report": "report",
        "analyzer_should_stop": False, "analyzer_reasoning": "", "objectives": [], "registered_scorers": [],
        "accepted_state": {"version": 0}, "tunable_params": {}, "capabilities": {}, "recent_decisions": [],
        "remaining_budget": {},
    }
