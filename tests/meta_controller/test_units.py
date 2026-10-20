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


def test_objective_ops_compose_with_accepted_ops():
    from scileo_agent.core.data_models import Objective
    from scileo_agent.meta_controller.schema import ObjectiveChange
    from scileo_agent.meta_controller.state import AcceptedState, apply_state_to_objectives, merge_change

    def scorer(*a, **k):
        return []

    registry = {"nominal": scorer, "center_distance": scorer, "smoothness": scorer}
    meta = {n: {"type": "candidate-wise", "description": n} for n in registry}
    raw = [Objective(name="nominal", description="n", optimization_direction="maximize", scorer=scorer),
           Objective(name="smoothness", description="s", optimization_direction="maximize", scorer=scorer)]
    state = AcceptedState()
    for ops in ([{"op": "add_from_registry", "name": "center_distance", "optimization_direction": "minimize", "weight": 1.0},
                 {"op": "drop", "name": "smoothness"}],
                [{"op": "set_weight", "name": "center_distance", "weight": 2.5}],      # edits an accepted addition
                [{"op": "add_from_registry", "name": "smoothness", "optimization_direction": "maximize"}]):  # undoes a drop
        state = merge_change(state, "objective", ObjectiveChange.model_validate({"ops": ops}))
        objectives, notes = apply_state_to_objectives(raw, state, registry.get, meta.get)
        assert notes == [], notes
    by_name = {o.name: o for o in objectives}
    assert set(by_name) == {"nominal", "center_distance", "smoothness"}
    assert by_name["center_distance"].weight == 2.5


def test_analyzer_accepts_missing_closing_reasoning_tag():
    """Original BasicAnalyzer parser: gpt-5-mini often omits </reasoning> at the very end (observed in real runs)."""
    from modules.shared.analyzer.basic_analyzer.basic_analyzer import BasicAnalyzer

    analyzer = BasicAnalyzer.__new__(BasicAnalyzer)
    analyzer.max_llm_retries = 0
    analyzer.enable_refusal_detection = False
    for text, expected in [
        ("<report>R</report>\n<should_stop>false</should_stop>\n<reasoning>keep going", "keep going"),
        ("<report>R</report>\n<should_stop>true</should_stop>\n<reasoning>done</reasoning>", "done"),
    ]:
        analyzer.call_llm_with_prompt = lambda *a, _t=text, **k: {"content": _t}
        out = asyncio.run(analyzer._get_llm_analysis("goal", None, "status", "objectives", "results", ""))
        assert out["reasoning"] == expected and out["analysis_report"] == "R"


def test_random_target_judge_proposals_are_schema_valid():
    from collections import Counter
    from modules.numeric_tasks.numeric_ga_optimizer import NumericGAOptimizer
    from scileo_agent.meta_controller.controller import LOOP_PARAM_SPECS
    from scileo_agent.meta_controller.judge import RandomTargetJudge

    specs = NumericGAOptimizer("ga", {"dim": 8}).tunable_params()
    specs.update({k: dict(v, current=0.0) for k, v in LOOP_PARAM_SPECS.items()})
    ctx = _ctx()
    ctx.update({
        "objectives": [{"name": "quality_score", "type": "candidate-wise", "scorer": "quality_score",
                        "description": "Quality score of the design in [0, 1]."},
                       {"name": "parameter_mean", "type": "candidate-wise", "scorer": "parameter_mean", "description": "x"}],
        "registered_scorers": [{"name": n, "type": "candidate-wise", "description": "d"} for n in ("quality_score", "parameter_mean", "parameter_spread")],
        "tunable_params": specs,
        "capabilities": {"allowed_targets": "objective, planning, implementation, optimization_workflow, no_change",
                         "objective.add_from_registry types": "candidate-wise"},
    })
    judge = RandomTargetJudge(seed=0)
    targets = Counter()
    for _ in range(300):
        out = asyncio.run(judge.decide(ctx))
        d, change, err = parse_decision(out.raw)
        assert err is None, (err, out.raw)
        targets[d.intervention_target] += 1
        if d.intervention_target == "optimization_workflow":
            (name, value), = change.params.items()
            assert specs[name]["min"] <= value <= specs[name]["max"]
    assert set(targets) == {"objective", "planning", "implementation", "optimization_workflow", "no_change"}
    assert min(targets.values()) > 30   # roughly uniform
