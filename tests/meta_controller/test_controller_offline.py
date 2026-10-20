"""
Offline tests of the real Meta-Controller inside the real OptimizationOrchestrator.

MOCK parts: rule-based planner, statistics analyzer, scripted judge, scripted validator (where noted),
fake LLM clients with synthetic token usage. REAL parts: orchestrator loop, controller, schema,
trial isolation, GA optimizer, scorer creator (name matching), knowledge manager, numeric
validators, in-process copies of the synthetic task scorers.
"""

import asyncio
import json

import pytest

from scileo_agent.core.registry.scorer_registry import get_scorer
from scileo_agent.meta_controller.controller import MetaController

from tests.meta_controller.helpers import (
    FAKE_SECRET, FakeLLMClient, ScriptedJudge, ScriptedValidator, decision, fingerprint, make_orchestrator,
    meta_config, no_change, register_inprocess_scorers, run,
)


GOOD_OBJECTIVES = {"spectrum_match": "maximize", "smoothness_v2": "maximize"}


def _records(orch):
    path = orch.output_dir / "meta_controller_decisions.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def _spy_step(orch):
    """Record fingerprints right before and after every controller step."""
    controller = orch.meta_controller
    original = controller.step
    snaps = []

    async def wrapped(**kwargs):
        before = fingerprint(orch)
        record = await original(**kwargs)
        snaps.append((before, fingerprint(orch), record))
        return record

    controller.step = wrapped
    return snaps


def _assert_unchanged(before, after, ignore=()):
    for key in before:
        if key not in ignore:
            assert before[key] == after[key], f"state '{key}' changed after a rejected/no-op step"


# --------------------------------------------------------------------------- disabled path
def test_disabled_controller_adds_no_calls(in_tmp, fresh_registry, monkeypatch):
    register_inprocess_scorers("spectral_signal")
    calls = []
    monkeypatch.setattr("scileo_agent.meta_controller.judge.LLMJudge.decide", lambda *a, **k: calls.append(1))
    monkeypatch.setattr(MetaController, "step", lambda *a, **k: calls.append(1))
    orch = make_orchestrator("disabled")
    assert orch.meta_controller is None and orch.budget_guard is None
    result = asyncio.run(run(orch))
    assert result.status == "completed" and result.termination_reason == "max_iterations"
    assert calls == []
    assert not (orch.output_dir / "meta_controller_decisions.jsonl").exists()
    stats = json.loads((orch.output_dir / "api_usage_statistics.json").read_text())
    assert "meta_controller" not in stats
    assert orch.planner.seen_guidance == [None, None, None]
    # one planner + one analyzer call per iteration, nothing else
    assert stats["total"]["call_count"] == 6


def test_explicitly_disabled_config_is_identical_to_absent(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("disabled2", meta={"enabled": False, "validator": "spectral_signal_truth"})
    assert orch.meta_controller is None and orch.budget_guard is None


# --------------------------------------------------------------------------- accept / reject with the real validator
def test_valid_implementation_fix_is_accepted_and_takes_effect(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("accept_rebind", meta=meta_config(), max_iterations=3)
    judge = ScriptedJudge([decision("implementation", {"objective_name": "smoothness", "action": "rebind_scorer",
                                                       "scorer_name": "smoothness_v2"}, failure_location="implementation")])
    orch.meta_controller.set_judge(judge)
    asyncio.run(run(orch))
    first = _records(orch)[0]
    assert first["outcome"] == "accepted", first["reason"]
    assert first["validation"]["delta"] > 0 and first["validation"]["candidate_mean"] > first["validation"]["baseline_mean"]
    assert first["decision"]["failure_location"] == "implementation"
    # the accepted binding is re-applied after scorer creation, so the old buggy scorer is not reused
    objectives_it2 = orch.knowledge_manager.get_objectives(2)
    smooth = next(o for o in objectives_it2 if o.name == "smoothness")
    assert smooth.metadata["meta_controller_scorer_binding"] == "smoothness_v2"
    assert smooth.scorer is get_scorer("smoothness_v2")
    final_values = [c.scores["smoothness"] for c in orch.current_population.candidates]
    assert all(v is not None and v <= 1.0 for v in final_values), "buggy (>1) cached values leaked into the final population"


def test_degrading_change_is_rejected_and_state_restored(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("reject_degrade", planner_objectives=GOOD_OBJECTIVES, meta=meta_config(), max_iterations=2)
    orch.meta_controller.set_judge(ScriptedJudge([decision("objective", {"ops": [
        {"op": "add_from_registry", "name": "smoothness", "optimization_direction": "maximize", "weight": 5.0}]})]))
    snaps = _spy_step(orch)
    asyncio.run(run(orch))
    before, after, record = snaps[0]
    assert record["outcome"] == "rejected" and "no_improvement" in record["reason"]
    assert record["validation"]["delta"] <= 0
    _assert_unchanged(before, after)
    assert set(after["registry"]) == set(before["registry"])
    # costs of the rejected attempt are kept
    assert record["costs"]["judge"]["llm_calls"] == 1
    assert record["costs"]["candidate"]["oracle_evals"] > 0 and record["costs"]["validation"]["oracle_evals"] > 0


def test_rescaled_objective_cannot_pass_validation(in_tmp, fresh_registry):
    """An objective change that only inflates objective scores (x1000) leaves true quality unchanged -> rejected."""
    import modules.numeric_tasks.scorer_mcp.spectral_signal_scorers_mcp.base as base

    inner = base.Scorer().scorers["spectrum_match"]["method"]
    scaled = lambda samples: [None if v is None else 1000.0 * v for v in inner(samples)]  # noqa: E731
    register_inprocess_scorers("spectral_signal", extra={
        "spectrum_match_x1000": (scaled, "candidate-wise", "Spectral match, reported on a 0-1000 scale.")})
    orch = make_orchestrator("rescale", planner_objectives=GOOD_OBJECTIVES, meta=meta_config(), max_iterations=2)
    orch.meta_controller.set_judge(ScriptedJudge([decision("implementation", {
        "objective_name": "spectrum_match", "action": "rebind_scorer", "scorer_name": "spectrum_match_x1000"})]))
    asyncio.run(run(orch))
    record = _records(orch)[0]
    assert record["outcome"] == "rejected"
    assert record["validation"]["delta"] == pytest.approx(0.0, abs=1e-12)


def test_trial_exception_is_rejected_with_costs_and_state_restored(in_tmp, fresh_registry):
    def broken(samples):
        raise RuntimeError("scorer crashed")
    register_inprocess_scorers("spectral_signal", extra={"smoothness_fast": (broken, "candidate-wise", "Fast smoothness.")})
    orch = make_orchestrator("trial_error", meta=meta_config(), max_iterations=2)
    orch.meta_controller.set_judge(ScriptedJudge([decision("implementation", {
        "objective_name": "smoothness", "action": "rebind_scorer", "scorer_name": "smoothness_fast"})]))
    snaps = _spy_step(orch)
    asyncio.run(run(orch))
    before, after, record = snaps[0]
    assert record["outcome"] == "rejected" and record["reason"].startswith("candidate_execution_failed")
    assert "candidate" in record["costs"]
    _assert_unchanged(before, after)


# --------------------------------------------------------------------------- every target triggers its real action
def test_planning_target_changes_planner_guidance(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("planning", meta=meta_config(), max_iterations=3)
    guidance = "Use the verified implementation: ADD:smoothness_v2:maximize REMOVE:smoothness"
    orch.meta_controller.set_judge(ScriptedJudge([decision("planning", {"guidance": guidance}, failure_location="implementation")]))
    calls_before_trials = []
    original = orch.meta_controller._validate

    async def spy(*args, **kwargs):
        calls_before_trials.append((orch.planner.call_count, len(orch.planner.message_history)))
        return await original(*args, **kwargs)

    orch.meta_controller._validate = spy
    asyncio.run(run(orch))
    record = _records(orch)[0]
    assert record["outcome"] == "accepted", record["reason"]
    assert record["validation"]["use_planner"] is True
    assert record["validation"]["candidate_objectives"] == ["spectrum_match", "smoothness_v2"]
    assert record["validation"]["baseline_objectives"] == ["spectrum_match", "smoothness"]
    # planner clone was used for trials: the live planner saw exactly one planning call per real iteration
    assert orch.planner.call_count == 3
    assert orch.planner.seen_guidance[0] is None and orch.planner.seen_guidance[1] == guidance
    assert [o.name for o in orch.knowledge_manager.get_objectives(2)] == ["spectrum_match", "smoothness_v2"]
    # trial planning calls were real (mock) LLM calls on the shared planner client and are costed
    assert record["costs"]["candidate"]["llm_calls"] == 1 and record["costs"]["validation"]["llm_calls"] == 1


def test_objective_target_reweights_objective_used_by_optimizer(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("objective", planner_objectives=GOOD_OBJECTIVES, meta=meta_config(), max_iterations=3)
    orch.meta_controller.validator = ScriptedValidator([0.1, 0.2])  # MOCK: force a measurable gain
    orch.meta_controller.set_judge(ScriptedJudge([decision("objective", {"ops": [
        {"op": "set_weight", "name": "smoothness_v2", "weight": 3.0}]})]))
    seen_weights = []
    original = orch.optimizer.optimize

    async def spy(population, objectives, **kwargs):
        seen_weights.append({o.name: o.weight for o in objectives})
        return await original(population, objectives, **kwargs)

    orch.optimizer.optimize = spy
    asyncio.run(run(orch))
    assert _records(orch)[0]["outcome"] == "accepted"
    assert seen_weights[0]["smoothness_v2"] is None
    assert seen_weights[1]["smoothness_v2"] == 3.0 and seen_weights[2]["smoothness_v2"] == 3.0


def test_sanitize_outputs_turns_out_of_range_into_failed(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("sanitize", meta=meta_config(), max_iterations=2)
    orch.meta_controller.validator = ScriptedValidator([0.1, 0.2])  # MOCK
    orch.meta_controller.set_judge(ScriptedJudge([decision("implementation", {
        "objective_name": "smoothness", "action": "sanitize_outputs", "valid_range": [0.0, 1.0]})]))
    asyncio.run(run(orch))
    assert _records(orch)[0]["outcome"] == "accepted"
    values = [c.scores["smoothness"] for c in orch.current_population.candidates]
    assert all(v is None or 0.0 <= v <= 1.0 for v in values)
    assert any(v is None for v in values)


def test_workflow_target_changes_parameters_where_they_are_read(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("workflow", meta=meta_config(), max_iterations=3)
    orch.meta_controller.validator = ScriptedValidator([0.1, 0.2])  # MOCK
    orch.meta_controller.set_judge(ScriptedJudge([decision("optimization_workflow", {
        "params": {"mutation_sigma": 0.25, "tournament_size": 5, "random_candidate_ratio": 0.25}})]))
    seen = []
    original = orch.optimizer.optimize

    async def spy(population, objectives, **kwargs):
        seen.append((orch.optimizer.mutation_sigma, orch.optimizer.tournament_size))
        return await original(population, objectives, **kwargs)

    orch.optimizer.optimize = spy
    asyncio.run(run(orch))
    assert _records(orch)[0]["outcome"] == "accepted"
    assert seen[0] == (0.08, 3) and seen[1] == (0.25, 5)
    assert orch.config.loop_config["random_candidate_ratio"] == 0.25
    tracking = json.loads((orch.output_dir / "run_process_tracking.json").read_text())
    replacement = [p for it in tracking["iterations"] for p in it["phases"] if p["phase_name"] == "optimization"]
    assert replacement[1]["random_candidate_replacement"]["num_replaced"] == 4   # 25% of 16, read by the orchestrator


def test_unsupported_and_invalid_actions_are_recorded_not_substituted(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    decisions = [
        decision("implementation", {"objective_name": "smoothness", "action": "rebuild_scorer",
                                    "instructions": "Fix the sign of the exponent so values stay in [0, 1]."}),
        decision("optimization_workflow", {"params": {"population_size": 64}}),
        decision("optimization_workflow", {"params": {"mutation_sigma": 0.9}}),
        decision("objective", {"ops": [{"op": "drop", "name": "not_an_objective"}]}),
        decision("objective", {"ops": [{"op": "add_from_registry", "name": "unknown_scorer", "optimization_direction": "maximize"}]}),
        decision("implementation", {"objective_name": "smoothness", "action": "rebind_scorer", "scorer_name": "smoothness"}),
        "<decision>{not json</decision>",
        RuntimeError(f"provider error {FAKE_SECRET}"),
        decision("objective", {"ops": [{"op": "set_weight", "name": "spectrum_match", "weight": 50}]}),
    ]
    expected = ["unsupported", "unsupported", "invalid_decision", "invalid_decision", "invalid_decision",
                "invalid_decision", "judge_error", "judge_error", "invalid_decision"]
    orch = make_orchestrator("invalid", meta=meta_config(), max_iterations=len(decisions) + 1)
    judge = ScriptedJudge(decisions)
    orch.meta_controller.set_judge(judge)
    snaps = _spy_step(orch)
    asyncio.run(run(orch))
    records = _records(orch)
    assert [r["outcome"] for r in records[: len(expected)]] == expected
    assert orch.meta_controller.trial_evals == 0 and orch.meta_controller.validation_evals == 0
    for before, after, record in snaps[: len(expected)]:
        _assert_unchanged(before, after)
    assert FAKE_SECRET not in (orch.output_dir / "meta_controller_decisions.jsonl").read_text()


def test_no_change_keeps_state_and_loop_continues(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("nochange", meta=meta_config(), max_iterations=3)
    orch.meta_controller.set_judge(ScriptedJudge([no_change(), no_change()]))
    snaps = _spy_step(orch)
    result = asyncio.run(run(orch))
    records = _records(orch)
    assert [r["outcome"] for r in records] == ["no_change", "no_change", "skipped"]
    assert "final_iteration" in records[2]["reason"]
    assert result.termination_reason == "max_iterations" and sorted(orch.knowledge_manager.populations_by_iteration) == [0, 1, 2, 3]
    assert orch.meta_controller.trial_evals == 0 and orch.meta_controller.state.version == 0
    for before, after, _ in snaps[:2]:
        _assert_unchanged(before, after)


def test_no_validator_never_accepts(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("novalidator", meta=meta_config(validator=None), max_iterations=2)
    orch.meta_controller.set_judge(ScriptedJudge([decision("implementation", {
        "objective_name": "smoothness", "action": "rebind_scorer", "scorer_name": "smoothness_v2"})]))
    asyncio.run(run(orch))
    record = _records(orch)[0]
    assert record["outcome"] == "rejected" and "no_independent_validator" in record["reason"]
    assert orch.meta_controller.state.version == 0


def test_analyzer_stop_is_respected_and_not_intervened(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("stop", meta=meta_config(), max_iterations=3, analyzer={"stop_at_iteration": 1})
    judge = ScriptedJudge([])
    orch.meta_controller.set_judge(judge)
    result = asyncio.run(run(orch))
    assert result.termination_reason == "early_stop" and judge.calls == 0
    assert _records(orch)[0]["outcome"] == "skipped"


# --------------------------------------------------------------------------- budget
def test_budget_exhaustion_prevents_interventions(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("budget", meta=meta_config(), budget={"max_llm_calls": 3}, max_iterations=5)
    judge = ScriptedJudge([decision("implementation", {"objective_name": "smoothness", "action": "rebind_scorer",
                                                       "scorer_name": "smoothness_v2"})])
    orch.meta_controller.set_judge(judge)
    result = asyncio.run(run(orch))
    records = _records(orch)
    assert judge.calls == 0
    assert all(r["outcome"] == "skipped" and r["reason"].startswith("budget_insufficient_before_judge") for r in records)
    assert result.termination_reason == "budget_exhausted"
    usage = json.loads((orch.output_dir / "budget_usage.json").read_text())
    assert usage["caps"] == {"max_llm_calls": 3} and usage["used"]["llm_calls"] >= 3


def test_same_budget_guard_applies_without_controller(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("budget_a", budget={"max_oracle_evals": 100}, max_iterations=5)
    assert orch.meta_controller is None and orch.budget_guard is not None
    result = asyncio.run(run(orch))
    assert result.termination_reason == "budget_exhausted"


def test_rejected_attempt_costs_are_kept_and_unknown_tokens_flagged(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("costs", meta=meta_config(), max_iterations=2)
    orch.meta_controller.validator = ScriptedValidator([0.5, 0.4])  # MOCK: candidate worse
    judge_client = FakeLLMClient(model="mock/judge", with_usage=False)
    orch.meta_controller.set_judge(ScriptedJudge([decision("planning", {"guidance": "ADD:smoothness_v2:maximize please"})],
                                                 client=judge_client))
    asyncio.run(run(orch))
    record = _records(orch)[0]
    assert record["outcome"] == "rejected"
    assert record["costs"]["judge"]["total_tokens"] is None and record["costs"]["judge"]["calls_missing_usage"] == 1
    assert record["costs"]["candidate"]["llm_calls"] == 1 and record["costs"]["candidate"]["total_tokens"] == 200
    assert record["costs"]["validation"]["llm_calls"] == 1
    assert record["costs"]["total"]["llm_calls"] == 3
    stats = json.loads((orch.output_dir / "api_usage_statistics.json").read_text())
    assert stats["meta_controller"]["call_count"] == 1           # judge client
    assert stats["planner"]["call_count"] == 2 + 2                # 2 real iterations + 2 trial plans (shared client)
    summary = json.loads((orch.output_dir / "meta_controller_summary.json").read_text())
    assert summary["outcomes"]["rejected"] == 1 and summary["acceptance_rate"] == 0.0


# --------------------------------------------------------------------------- v2 additions
def test_random_target_judge_runs_through_controller(in_tmp, fresh_registry):
    register_inprocess_scorers("overflow_scorer")
    orch = make_orchestrator("random_judge", task_id="overflow_scorer",
                             meta=meta_config("overflow_scorer", judge={"type": "random", "seed": 3}, max_ops_per_change=1),
                             max_iterations=6)
    assert orch.meta_controller.judge.judge_type == "random_target_control"
    asyncio.run(run(orch, "overflow_scorer"))
    records = _records(orch)
    assert all(r["judge"]["judge_type"] == "random_target_control" for r in records)
    assert all(r["outcome"] in ("accepted", "rejected", "no_change", "skipped", "unsupported") for r in records), \
        [(r["outcome"], r["reason"]) for r in records]
    stats = json.loads((orch.output_dir / "api_usage_statistics.json").read_text())
    assert stats["meta_controller"]["call_count"] == 0     # the control judge makes no LLM calls


def test_max_ops_per_change_is_enforced(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch = make_orchestrator("maxops", meta=meta_config(max_ops_per_change=1), max_iterations=2)
    orch.meta_controller.set_judge(ScriptedJudge([decision("objective", {"ops": [
        {"op": "set_weight", "name": "spectrum_match", "weight": 2.0}, {"op": "drop", "name": "smoothness"}]})]))
    asyncio.run(run(orch))
    record = _records(orch)[0]
    assert record["outcome"] == "invalid_decision" and "at most 1" in record["reason"]


def test_stop_on_analyzer_decision_flag_applies_to_all_arms(in_tmp, fresh_registry):
    register_inprocess_scorers("spectral_signal")
    orch_a = make_orchestrator("nostop_a", max_iterations=3, analyzer={"stop_at_iteration": 1},
                               loop_extra={"stop_on_analyzer_decision": False})
    result = asyncio.run(run(orch_a))
    assert result.termination_reason == "max_iterations" and orch_a.current_iteration == 3
    orch_b = make_orchestrator("nostop_b", meta=meta_config(), max_iterations=3, analyzer={"stop_at_iteration": 1},
                               loop_extra={"stop_on_analyzer_decision": False})
    judge = ScriptedJudge([no_change(), no_change()])
    orch_b.meta_controller.set_judge(judge)
    asyncio.run(run(orch_b))
    assert judge.calls == 2 and [r["outcome"] for r in _records(orch_b)][:2] == ["no_change", "no_change"]


def test_judge_context_has_analyzer_independent_diagnostics(in_tmp, fresh_registry):
    register_inprocess_scorers("overflow_scorer")
    orch = make_orchestrator("diag", task_id="overflow_scorer", meta=meta_config("overflow_scorer"), max_iterations=2,
                             ga={"mutation_sigma": 0.005, "crossover_rate": 0.0})
    judge = ScriptedJudge([no_change()])
    orch.meta_controller.set_judge(judge)
    asyncio.run(run(orch, "overflow_scorer"))
    diag = judge.contexts[0]["diagnostics"]
    q = diag["objective_scores_current_population"]["quality_score"]
    assert q["declared_range"] == [0.0, 1.0] and q["n_outside_declared_range"] > 0 and q["max"] > 1.0
    status = diag["tunable_parameter_status"]
    assert status["mutation_sigma"]["at_lower_bound"] is True and status["mutation_sigma"]["default"] == 0.08
    assert status["crossover_rate"]["at_lower_bound"] is True
    assert diag["optimizer_reported_last_run"]["mean_child_parent_distance"] is not None
    assert {"per_dimension_std_mean", "mean_pairwise_distance"} <= set(diag["population_diversity"])
    assert diag["best_score_by_iteration_last6"]["quality_score"]
