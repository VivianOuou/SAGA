"""
Intervention-aware Meta-Controller (opt-in; disabled unless loop_config["meta_controller"]["enabled"]).

Insertion point in OptimizationOrchestrator.run(): right after the Analysis phase of iteration t
and before the analyzer's stop decision is acted on. The controller never changes should_stop.

Per iteration (at most one candidate):
    accepted state S -> Judge proposes change -> candidate S' = S + change (validated, bounded)
    -> candidate and baseline are executed in isolation (cloned planner, fresh scorer-creator and
       optimizer instances, deep-copied population, same seeds and evaluation quota)
    -> a fixed validator re-scores both populations on its validation split
    -> accept (S := S') or reject (S unchanged, trial artifacts removed); costs are always kept.

Scope: this improves the run based on the Analyzer's report. It does not recover from arbitrary
runtime exceptions raised before the Analyzer runs (those still terminate the run as before).
"""

import copy
import json
import random
import re
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..core.data_models import Objective, Population
from ..core.registry.scorer_registry import ScorerManager, get_scorer, get_scorer_metadata, list_scorers
from ..utils.logging import get_logger
from .budget import BudgetTracker
from .decision_log import DecisionLog
from .judge import BaseJudge, LLMJudge
from .schema import TARGETS, change_fingerprint, parse_decision
from .state import AcceptedState, apply_state_to_objectives, merge_change, patched_objective_names
from .validators import VALIDATION_SPLIT, BaseValidator, get_validator


logger = get_logger()


# Loop-level parameters the controller may change; each is read by the orchestrator where it acts.
LOOP_PARAM_SPECS = {
    "random_candidate_ratio": {
        "type": "float", "min": 0.0, "max": 0.5,
        "description": "Fraction of the incoming population replaced by random candidates before optimization "
                       "(read by the orchestrator's optimization phase from iteration 2 on).",
    },
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "task_id": None,
    "seed": None,
    "judge": {"type": "llm", "model_name": None, "max_retries": 2, "max_parse_retries": 1, "call_args": {}},
    "allowed_targets": list(TARGETS),
    "validator": None,
    "validation": {
        "seeds": [0],
        # Fixed before the run: accept iff (candidate - baseline) > 0 and >= min_improvement.
        "min_improvement": 0.0,
        "trial_optimizer_overrides": {},
        "seed_key": "seed",
        # Budget price of one validator evaluation in oracle-eval units (e.g. 10 = a lab assay costs 10 proxy evals).
        "cost_multiplier": 1.0,
    },
    "estimates": {"judge_tokens": 8000, "planner_call_tokens": 8000},
    "reserve_main_iteration": True,
    # Optional cap on ops per proposal (objective ops / workflow params); None = schema limit (3).
    "max_ops_per_change": None,
    "decision_log": "meta_controller_decisions.jsonl",
    "trial_root": None,
}


class TrialError(RuntimeError):
    pass


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _add_costs(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Sum two cost deltas; an unknown (None) count stays unknown."""
    out = dict(a)
    for key, value in b.items():
        mine = a.get(key)
        if isinstance(value, (int, float)) and isinstance(mine, (int, float)):
            out[key] = round(mine + value, 6) if isinstance(value, float) or isinstance(mine, float) else mine + value
        elif value is None or mine is None:
            out[key] = None
    return out


def _truncate(text: Optional[str], n: int) -> str:
    text = text or ""
    return text if len(text) <= n else text[: n - 15] + " ...[truncated]"


class _MergedClientView:
    """Read-only view that lets the orchestrator's usage reporting include controller-owned clients."""

    def __init__(self, clients_fn):
        self._clients_fn = clients_fn

    def _clients(self):
        seen, out = set(), []
        for c in self._clients_fn():
            if c is not None and id(c) not in seen:
                seen.add(id(c))
                out.append(c)
        return out

    def get_stats(self) -> Dict[str, Any]:
        merged: Dict[str, Dict[str, Any]] = {}
        for client in self._clients():
            for model, stats in client.get_stats().items():
                slot = merged.setdefault(model, {k: 0 for k in stats})
                for k, v in stats.items():
                    slot[k] = slot.get(k, 0) + (v or 0)
        return merged

    @property
    def responses(self) -> List[Any]:
        out = []
        for client in self._clients():
            out.extend(getattr(client, "responses", []) or [])
        return out


class _UsageModule:
    def __init__(self, clients_fn):
        self.llm_client = _MergedClientView(clients_fn)


class MetaController:
    def __init__(self, orchestrator, config: Dict[str, Any], judge: Optional[BaseJudge], validator: Optional[BaseValidator]):
        self.orch = orchestrator
        self.cfg = config
        self.validation_cfg = copy.deepcopy(config["validation"])  # frozen acceptance rule
        self.allowed_targets = set(config["allowed_targets"])
        unknown = self.allowed_targets - set(TARGETS)
        if unknown:
            raise ValueError(f"Unknown targets in allowed_targets: {sorted(unknown)}")
        self.judge: Optional[BaseJudge] = None
        self.validator = validator
        self.budget: Optional[BudgetTracker] = None
        self.state = AcceptedState()
        self.extra_clients: List[Any] = []
        self.trial_evals = 0
        self.validation_evals = 0           # budget units (raw evaluations x cost_multiplier)
        self.validation_evals_raw = 0
        self.records: List[Dict[str, Any]] = []
        self.log = DecisionLog(Path(orchestrator.output_dir) / config["decision_log"])
        self.trial_root = Path(config["trial_root"] or (Path(orchestrator.run_dir) / "meta_controller" / "trials"))
        self._raw_objectives: Optional[List[Objective]] = None
        self._start_snapshot = None
        self._last_step_snapshot = None
        self._main_iteration_costs: List[Dict[str, Any]] = []
        if judge is not None:
            self.set_judge(judge)

    # ------------------------------------------------------------------ wiring
    def set_judge(self, judge: BaseJudge) -> None:
        self.judge = judge
        for client in judge.llm_clients:
            if client not in self.extra_clients:
                self.extra_clients.append(client)

    def attach_budget(self, budget: BudgetTracker) -> None:
        self.budget = budget
        self._start_snapshot = budget.snapshot()

    def usage_module(self) -> _UsageModule:
        return _UsageModule(lambda: self.extra_clients)

    # ------------------------------------------------------------------ applying the accepted state
    def apply_accepted_state(self, objectives: List[Objective]) -> List[Objective]:
        """Called by the orchestrator after each scorer-creation phase."""
        self._raw_objectives = list(objectives)
        if not (self.state.objective_ops or self.state.implementation_patches):
            return objectives
        patched, notes = apply_state_to_objectives(objectives, self.state, get_scorer, get_scorer_metadata)
        self._clear_all_stat_caches(patched_objective_names(self.state))
        self.orch.knowledge_manager.store_objectives(patched, self.orch.current_iteration)
        self.orch.run_tracker.add_phase(
            iteration_number=self.orch.current_iteration,
            phase_name="meta_controller_apply",
            phase_data={
                "accepted_state_version": self.state.version,
                "objectives_after_patch": [
                    {"name": o.name, "weight": o.weight, "direction": o.optimization_direction,
                     "binding": o.metadata.get("meta_controller_scorer_binding"),
                     "sanitized_range": o.metadata.get("meta_controller_sanitized_range")}
                    for o in patched
                ],
                "notes": notes,
            },
        )
        logger.info(f"[MetaController] applied accepted state v{self.state.version} to objectives: "
                    f"{[o.name for o in patched]}" + (f" notes={notes}" if notes else ""))
        return patched

    def _clear_all_stat_caches(self, names: List[str]) -> None:
        """Drop cached statistics for patched objectives on the current population AND every population kept by
        the knowledge manager (the Analyzer re-scores the previous iteration's population, which is a different
        object than the current one once a trial population has been adopted)."""
        populations = [self.orch.current_population]
        populations.extend(getattr(self.orch.knowledge_manager, "populations_by_iteration", {}).values())
        seen = set()
        for population in populations:
            if population is not None and id(population) not in seen:
                seen.add(id(population))
                self._clear_stat_cache(population, names)

    @staticmethod
    def _clear_stat_cache(population: Optional[Population], names: List[str]) -> None:
        if population is None:
            return
        for attr in ("regular_scores_mean", "regular_scores_std", "regular_scores_none_count"):
            cache = getattr(population, attr, None)
            if isinstance(cache, dict):
                for name in names:
                    cache.pop(name, None)

    # ------------------------------------------------------------------ main entry
    async def step(
        self,
        iteration: int,
        max_iterations: int,
        analysis_result: Dict[str, Any],
        objectives: List[Objective],
        high_level_goal: str,
        context_information: Optional[str],
    ) -> Dict[str, Any]:
        snap0 = self.budget.snapshot()
        reference = self._last_step_snapshot or self._start_snapshot
        if reference is not None:
            self._main_iteration_costs.append(BudgetTracker.delta(reference, snap0))

        record: Dict[str, Any] = {
            "schema_version": 1,
            "timestamp": datetime.now().isoformat(),
            "run_id": self.orch.run_id,
            "task_id": self.cfg.get("task_id"),
            "seed": self.cfg.get("seed"),
            "iteration": iteration,
            "mode": "meta_controller_on",
            "judge": self.judge.describe() if self.judge else None,
            "validator": self.validator.describe() if self.validator else None,
            "acceptance_rule": {
                "split": VALIDATION_SPLIT,
                "seeds": list(self.validation_cfg["seeds"]),
                "min_improvement": self.validation_cfg["min_improvement"],
                "rule": "accept iff all trials ran, no constraint violation, budget not exceeded, "
                        "and mean(candidate) - mean(baseline) > 0 and >= min_improvement",
            },
            "accepted_state_version_before": self.state.version,
            "decision": None,
            "notes": [],
        }
        costs: Dict[str, Any] = {}
        try:
            outcome, reason = await self._step_inner(
                record, costs, iteration, max_iterations, analysis_result, objectives,
                high_level_goal, context_information,
            )
        except Exception as e:  # never let the controller kill the run; keep the accepted state
            outcome, reason = "controller_error", f"{type(e).__name__}: {e}"
            record["traceback"] = traceback.format_exc()[-4000:]
            logger.error(f"[MetaController] error at iteration {iteration}: {reason}")

        record["outcome"] = outcome
        record["reason"] = reason
        record["accepted_state_version_after"] = self.state.version
        record["accepted_state_after"] = self.state.to_dict()
        costs["total"] = BudgetTracker.delta(snap0, self.budget.snapshot())
        record["costs"] = costs
        record["budget"] = self.budget.report()
        self._last_step_snapshot = self.budget.snapshot()

        self.records.append(record)
        self.log.write(record)
        compact = {k: v for k, v in record.items() if k not in ("judge_raw_output", "traceback")}
        self.orch.run_tracker.add_phase(iteration_number=iteration, phase_name="meta_controller", phase_data=compact)
        self.orch.run_tracker.save()
        target = (record.get("decision") or {}).get("intervention_target")
        logger.info(f"[MetaController] iteration {iteration}: target={target} outcome={outcome} ({_truncate(reason, 300)})")
        return record

    async def _step_inner(self, record, costs, iteration, max_iterations, analysis_result, objectives,
                          high_level_goal, context_information) -> Tuple[str, str]:
        if analysis_result.get("should_stop") and self.orch.config.loop_config.get("stop_on_analyzer_decision", True):
            return "skipped", "analyzer_should_stop (stop logic unchanged; no intervention attempted)"
        if iteration >= max_iterations:
            return "skipped", "final_iteration (no later iteration could use an accepted change)"
        if self.judge is None:
            return "skipped", "no_judge_configured"

        ok, why = self.budget.can_afford(self._estimate(target=None, include_judge=True))
        if not ok:
            return "skipped", f"budget_insufficient_before_judge: {why}"

        # -------- 1. propose
        if self._raw_objectives is None:
            self._raw_objectives = list(objectives)
        self._current_objectives = list(objectives)
        context = self._judge_context(iteration, max_iterations, analysis_result, objectives, high_level_goal)
        snap = self.budget.snapshot()
        out = await self.judge.decide(context)
        costs["judge"] = BudgetTracker.delta(snap, self.budget.snapshot())
        costs["judge"]["attempts"] = out.attempts
        record["judge_raw_output"] = _truncate(out.raw_text, 8000)
        if out.error:
            return "judge_error", out.error

        decision, change, error = parse_decision(out.raw)
        if error:
            record["judge_raw_decision"] = out.raw
            return "invalid_decision", error
        record["decision"] = {
            "failure_location": decision.failure_location,
            "root_cause_hypothesis": decision.root_cause_hypothesis,
            "intervention_target": decision.intervention_target,
            "rationale": decision.rationale,
            "proposed_change": decision.proposed_change,
            "expected_benefit_hypothesis": decision.expected_benefit,
            "validation_plan_suggested_by_judge": decision.validation_plan,
            "self_reported_confidence_uncalibrated": decision.confidence,
            "target_assessment": decision.target_assessment,
        }
        target = decision.intervention_target
        if target == "no_change":
            return "no_change", "judge chose no_change: accepted state kept; the native SAGA loop continues to the next iteration"
        if target not in self.allowed_targets:
            return "invalid_decision", f"target '{target}' is disabled by configuration"
        record["change_id"] = change_fingerprint(target, change)

        # -------- 2. build the candidate state (live-context checks)
        status, reason, candidate_state, meta = self._build_candidate(target, change, iteration)
        if status != "ok":
            return status, reason
        record["candidate_state"] = candidate_state.to_dict()

        if self.validator is None:
            return "rejected", "no_independent_validator_configured (changes are never accepted without one)"
        ok, why = self.budget.can_afford(self._estimate(target=target, include_judge=False))
        if not ok:
            return "rejected", f"budget_insufficient_for_validation: {why}"

        # -------- 3. isolated execution + independent validation
        accept, reason = await self._validate(
            iteration, target, candidate_state, meta, high_level_goal, context_information,
            analysis_result, costs, record,
        )
        if accept:
            self._commit(candidate_state, target)
            return "accepted", reason
        return "rejected", reason

    # ------------------------------------------------------------------ candidate construction
    def _tunable_specs(self) -> Dict[str, Dict[str, Any]]:
        specs: Dict[str, Dict[str, Any]] = {}
        optimizer = self.orch.optimizer
        if hasattr(optimizer, "tunable_params") and hasattr(optimizer, "set_tunable_params"):
            for name, spec in optimizer.tunable_params().items():
                specs[name] = dict(spec, scope="optimizer")
        for name, spec in LOOP_PARAM_SPECS.items():
            specs[name] = dict(spec, scope="loop", current=self.orch.config.loop_config.get(name, 0.0))
        return specs

    def _rebuild_support(self) -> Tuple[bool, str]:
        creator = self.orch.scorer_creator
        if getattr(creator, "scorer_implementor", None) is None or not hasattr(creator, "_create_scorer_with_llm_async"):
            return False, ("unsupported: requires the coding-agent scorer implementor "
                           "(scorer_creator enable_llm_scorer_creation=True with a Claude Code model)")
        if not self.orch.serializer_name:
            return False, "unsupported: no serializer configured for scorer generation"
        return True, "supported"

    def _allowed_objective_types(self) -> List[str]:
        planner = self.orch.planner
        types = ["candidate-wise"]
        if getattr(planner, "support_population_wise", False):
            types.append("population-wise")
        if getattr(planner, "support_filter", False):
            types.append("filter")
        return types

    def _objective_signature(self, objectives: List[Objective]) -> List[Tuple]:
        return sorted((o.name, o.weight, o.optimization_direction, id(o.scorer)) for o in objectives)

    def _build_candidate(self, target: str, change, iteration: int) -> Tuple[str, str, Optional[AcceptedState], Dict[str, Any]]:
        meta: Dict[str, Any] = {}
        current = {o.name: o for o in self._current_objectives}
        registered = set(list_scorers())

        max_ops = self.cfg.get("max_ops_per_change")
        n_ops = len(change.ops) if target == "objective" else len(change.params) if target == "optimization_workflow" else 1
        if max_ops is not None and n_ops > max_ops:
            return "invalid_decision", f"{n_ops} ops proposed; at most {max_ops} per change in this configuration", None, meta

        if target == "objective":
            allowed_types = self._allowed_objective_types()
            for op in change.ops:
                if op.op in ("set_weight", "drop") and op.name not in current:
                    return "invalid_decision", f"objective '{op.name}' is not in the current objective set", None, meta
                if op.op == "add_from_registry":
                    if op.name in current:
                        return "invalid_decision", f"'{op.name}' is already an objective", None, meta
                    if op.name not in registered:
                        return "invalid_decision", f"scorer '{op.name}' is not registered", None, meta
                    scorer_type = (get_scorer_metadata(op.name) or {}).get("type", "candidate-wise")
                    if scorer_type not in allowed_types:
                        return "unsupported", f"objective type '{scorer_type}' is not supported by the planner/optimizer configuration", None, meta
                    if scorer_type != "filter" and op.optimization_direction is None:
                        return "invalid_decision", f"add_from_registry('{op.name}') requires optimization_direction", None, meta
            try:
                candidate = merge_change(self.state, target, change)
            except ValueError as e:
                return "invalid_decision", str(e), None, meta
            before, old_notes = apply_state_to_objectives(self._raw_objectives, self.state, get_scorer, get_scorer_metadata)
            after, notes = apply_state_to_objectives(self._raw_objectives, candidate, get_scorer, get_scorer_metadata)
            new_notes = [n for n in notes if n not in old_notes]
            if new_notes:
                return "invalid_decision", f"change does not apply cleanly: {new_notes}", None, meta
            if self._objective_signature(before) == self._objective_signature(after):
                return "invalid_decision", "change has no effect on the objective set", None, meta
            return "ok", "", candidate, meta

        if target == "planning":
            if not hasattr(self.orch.planner, "set_strategy_guidance"):
                return "unsupported", "planner does not expose set_strategy_guidance()", None, meta
            candidate = merge_change(self.state, target, change)
            if candidate.planner_guidance == self.state.planner_guidance:
                return "invalid_decision", "guidance identical to the accepted guidance", None, meta
            meta["needs_planner"] = True
            return "ok", "", candidate, meta

        if target == "implementation":
            obj = current.get(change.objective_name)
            if obj is None:
                return "invalid_decision", f"objective '{change.objective_name}' is not in the current objective set", None, meta
            if change.action == "rebind_scorer":
                if change.scorer_name not in registered:
                    return "invalid_decision", f"scorer '{change.scorer_name}' is not registered", None, meta
                scorer_type = (get_scorer_metadata(change.scorer_name) or {}).get("type", "candidate-wise")
                if scorer_type != obj.type:
                    return "invalid_decision", f"type mismatch: objective is {obj.type}, scorer is {scorer_type}", None, meta
                if get_scorer(change.scorer_name) is obj.scorer:
                    return "invalid_decision", "objective is already bound to this scorer", None, meta
            elif change.action == "sanitize_outputs":
                if obj.type != "candidate-wise":
                    return "unsupported", "sanitize_outputs is only supported for candidate-wise objectives", None, meta
            elif change.action == "rebuild_scorer":
                supported, why = self._rebuild_support()
                if not supported:
                    return "unsupported", f"rebuild_scorer {why}", None, meta
                meta["rebuild"] = {
                    "objective": obj,
                    "versioned_name": f"{obj.name}__mc_v{self.state.version + 1}_it{iteration}",
                    "instructions": change.instructions,
                }
            candidate = merge_change(self.state, target, change)
            if change.action == "rebuild_scorer":
                candidate.implementation_patches[change.objective_name]["scorer_name"] = meta["rebuild"]["versioned_name"]
            return "ok", "", candidate, meta

        if target == "optimization_workflow":
            specs = self._tunable_specs()
            if not specs:
                return "unsupported", "no tunable optimization/workflow parameters are exposed", None, meta
            changed = False
            for name, value in change.params.items():
                spec = specs.get(name)
                if spec is None:
                    return "unsupported", f"parameter '{name}' is not exposed (allowed: {sorted(specs)})", None, meta
                if not (spec["min"] <= value <= spec["max"]):
                    return "invalid_decision", f"parameter '{name}'={value} outside [{spec['min']}, {spec['max']}]", None, meta
                if spec["type"] == "int" and float(value) != int(value):
                    return "invalid_decision", f"parameter '{name}' must be an integer", None, meta
                if spec.get("current") != value:
                    changed = True
            if not changed:
                return "invalid_decision", "all parameters already have the proposed values", None, meta
            normalized = type(change)(params={k: (int(v) if specs[k]["type"] == "int" else float(v)) for k, v in change.params.items()})
            return "ok", "", merge_change(self.state, target, normalized), meta

        return "invalid_decision", f"unknown target '{target}'", None, meta

    # ------------------------------------------------------------------ isolated trials
    def _clone_planner(self):
        planner = self.orch.planner
        clone = copy.copy(planner)
        for attr in ("message_history", "objective_planning_response_dicts", "metadata", "attached_scorers"):
            if hasattr(planner, attr):
                setattr(clone, attr, copy.deepcopy(getattr(planner, attr)))
        return clone

    def _new_module(self, module_type: str, **overrides):
        module = self.orch._create_module_from_config(module_type, **overrides)
        if getattr(module, "llm_client", None) is not None and module.llm_client not in self.extra_clients:
            self.extra_clients.append(module.llm_client)
        return module

    async def _trial_objectives(self, state: AcceptedState, use_planner: bool, iteration: int, trial_dir: Path,
                                high_level_goal: str, context_information: Optional[str], analysis_report: str,
                                seed: int) -> List[Objective]:
        if not use_planner:
            objectives, _ = apply_state_to_objectives(self._raw_objectives, state, get_scorer, get_scorer_metadata)
            return objectives
        planner = self._clone_planner()
        planner.set_strategy_guidance(state.planner_guidance)
        plan = await planner.process(
            iteration_number=iteration + 1,
            high_level_goal=high_level_goal,
            context_information=context_information,
            initial_objectives=None,
            analysis_report=analysis_report,
            mode="normal",
        )
        creator = self._new_module(
            "scorer_creator",
            coding_workspace_path=str(trial_dir / "coding_workspace"),
            generated_scorer_library_path=str(trial_dir / "generated_scorers"),
        )
        population = self.orch.current_population
        test_candidates = None
        if population is not None and population.size > 0:
            test_candidates = random.Random(seed).sample(population.candidates, min(10, population.size))
        matched = await creator.process(plan["objectives"], serializer_name=self.orch.serializer_name, test_candidates=test_candidates)
        objectives = matched["matched_objectives"]
        if not [o for o in objectives if o.type != "filter"]:
            raise TrialError("no planned objective could be matched to a scorer")
        objectives, _ = apply_state_to_objectives(objectives, state, get_scorer, get_scorer_metadata)
        return objectives

    async def _trial_optimize(self, objectives: List[Objective], state: AcceptedState, seed: int, high_level_goal: str,
                              optimizer=None, population: Optional[Population] = None, stage: int = 1):
        """One trial iteration. Stage 1 starts a fresh optimizer from (a copy of) the current population;
        later stages (sequential validation) continue the same optimizer and trial population."""
        if optimizer is None:
            overrides = dict(self.validation_cfg.get("trial_optimizer_overrides") or {})
            seed_key = self.validation_cfg.get("seed_key")
            if seed_key:
                overrides[seed_key] = seed
            optimizer = self._new_module("optimizer", **overrides)
            optimizer_params = {k: v for k, v in state.workflow_params.items() if k not in LOOP_PARAM_SPECS}
            if optimizer_params:
                optimizer.set_tunable_params(optimizer_params)
        if population is None:
            population = copy.deepcopy(self.orch.current_population)

        ratio = state.workflow_params.get("random_candidate_ratio", self.orch.config.loop_config.get("random_candidate_ratio", 0.0))
        if ratio > 0 and population is not None and population.size > 0:
            n_replace = int(population.size * ratio)
            if n_replace > 0:
                randoms = await optimizer.create_random_candidates(n_replace)
                rng = random.Random(seed if stage == 1 else seed * 1000 + stage)
                indices = sorted(rng.sample(range(population.size), n_replace))
                candidates = list(population.candidates)
                for j, i in enumerate(indices):
                    candidates[i] = randoms[j]
                population = Population(candidates=candidates)

        evals_before = getattr(optimizer, "num_evaluations", 0) or 0
        try:
            result = await optimizer.process(current_population=population, objectives=objectives, high_level_goal=high_level_goal)
        finally:
            self.trial_evals += (getattr(optimizer, "num_evaluations", 0) or 0) - evals_before
        return result, optimizer

    def _validate_population(self, population: Population):
        result = self.validator.evaluate([c.representation for c in population.candidates], split=VALIDATION_SPLIT)
        self.validation_evals_raw += int(result.n_evals)
        self.validation_evals += int(round(result.n_evals * self._validation_cost_multiplier()))
        return result

    def _validation_cost_multiplier(self) -> float:
        return float(self.validation_cfg.get("cost_multiplier", 1.0))

    async def _rebuild_scorer(self, meta: Dict[str, Any], trial_dir: Path) -> None:
        info = meta["rebuild"]
        source: Objective = info["objective"]
        creator = self._new_module(
            "scorer_creator",
            coding_workspace_path=str(trial_dir / "coding_workspace"),
            generated_scorer_library_path=str(trial_dir / "generated_scorers"),
        )
        spec = Objective(
            name=info["versioned_name"],
            description=f"{source.description}\n\nImplementation fix requested (meaning unchanged): {info['instructions']}",
            type=source.type,
            optimization_direction=source.optimization_direction,
        )
        population = self.orch.current_population
        test_candidates = population.candidates[: min(10, population.size)] if population else None
        scorer = await creator._create_scorer_with_llm_async(spec, None, self.orch.serializer_name, test_candidates)
        if scorer is None or get_scorer(info["versioned_name"]) is None:
            raise TrialError(f"scorer rebuild produced no registered scorer named '{info['versioned_name']}'")

    @staticmethod
    def _gate_decision(mode: str, delta: float, stage: int, max_stages: int, min_improvement: float, reject_margin: float) -> str:
        """Fixed acceptance rule: 'accept' | 'reject' | 'continue' (continue only in sequential mode)."""
        if delta > 0 and delta >= min_improvement:
            return "accept"
        if mode != "sequential" or stage >= max_stages or delta <= reject_margin:
            return "reject"
        return "continue"

    def _stage_estimate(self) -> Dict[str, float]:
        """Cost of one more validation stage (both sides, all seeds, plus re-validation)."""
        est = {"llm_calls": 0.0, "total_tokens_observed": 0.0, "oracle_evals": 0.0}
        optimizer = self.orch.optimizer
        if hasattr(optimizer, "estimate_evaluations"):
            per_trial = optimizer.estimate_evaluations(**(self.validation_cfg.get("trial_optimizer_overrides") or {}))
            pop_size = self.orch.current_population.size if self.orch.current_population else 0
            est["oracle_evals"] = 2 * len(self.validation_cfg["seeds"]) * (per_trial + pop_size * self._validation_cost_multiplier())
        return est

    async def _validate(self, iteration, target, candidate_state, meta, high_level_goal, context_information,
                        analysis_result, costs, record) -> Tuple[bool, str]:
        seeds = list(self.validation_cfg["seeds"])
        mode = self.validation_cfg.get("mode", "single")
        max_stages = int(self.validation_cfg.get("max_stages", 1)) if mode == "sequential" else 1
        reject_margin = float(self.validation_cfg.get("reject_margin", 0.0))
        min_improvement = float(self.validation_cfg["min_improvement"])
        use_planner = bool(meta.get("needs_planner"))
        trial_dir = self.trial_root / f"iter_{iteration}"
        registry_before = set(list_scorers())
        keep_scorers = set()
        py_state, np_state = random.getstate(), np.random.get_state()
        analysis_report = analysis_result["analysis_report"]
        validation: Dict[str, Any] = {"seeds": seeds, "use_planner": use_planner, "mode": mode, "max_stages": max_stages}
        record["validation"] = validation
        accept, reason = False, "not evaluated"

        try:
            # ---- stage 1: candidate execution (counted as "candidate")
            snap = self.budget.snapshot()
            cand_runs = []
            try:
                if meta.get("rebuild"):
                    await self._rebuild_scorer(meta, trial_dir)
                    keep_scorers.add(meta["rebuild"]["versioned_name"])
                cand_objectives = await self._trial_objectives(candidate_state, use_planner, iteration, trial_dir,
                                                               high_level_goal, context_information, analysis_report, seeds[0])
                validation["candidate_objectives"] = [o.name for o in cand_objectives]
                for seed in seeds:
                    cand_runs.append(await self._trial_optimize(cand_objectives, candidate_state, seed, high_level_goal))
            except Exception as e:
                return False, f"candidate_execution_failed: {type(e).__name__}: {e}"
            finally:
                costs["candidate"] = BudgetTracker.delta(snap, self.budget.snapshot())

            # ---- stage 1: baseline execution + independent re-scoring of both sides (counted as "validation")
            snap = self.budget.snapshot()
            try:
                base_objectives = await self._trial_objectives(self.state, use_planner, iteration, trial_dir,
                                                               high_level_goal, context_information, analysis_report, seeds[0])
                validation["baseline_objectives"] = [o.name for o in base_objectives]
                base_runs = [await self._trial_optimize(base_objectives, self.state, seed, high_level_goal) for seed in seeds]
                base_results = [self._validate_population(p) for p, _ in base_runs]
                cand_results = [self._validate_population(p) for p, _ in cand_runs]
            except Exception as e:
                return False, f"validation_failed: {type(e).__name__}: {e}"
            finally:
                costs["validation"] = BudgetTracker.delta(snap, self.budget.snapshot())

            stages, stage = [], 1
            while True:
                base_mean = float(np.mean([r.metric for r in base_results]))
                cand_mean = float(np.mean([r.metric for r in cand_results]))
                delta = cand_mean - base_mean if self.validator.higher_is_better else base_mean - cand_mean
                stages.append({"stage": stage, "baseline": [r.metric for r in base_results],
                               "candidate": [r.metric for r in cand_results], "delta": delta})
                decision = self._gate_decision(mode, delta, stage, max_stages, min_improvement, reject_margin)
                violation = any(r.constraint_violation for r in cand_results)
                exhausted, why = self.budget.exhausted()
                if violation or exhausted or decision != "continue":
                    break
                ok, why_budget = self.budget.can_afford(self._stage_estimate())
                if not ok:
                    decision = "reject_budget"
                    break
                # ---- next stage: continue both sides by one iteration with the same seeds
                stage += 1
                snap = self.budget.snapshot()
                try:
                    cand_runs = [await self._trial_optimize(cand_objectives, candidate_state, seed, high_level_goal,
                                                            optimizer=opt, population=pop, stage=stage)
                                 for (pop, opt), seed in zip(cand_runs, seeds)]
                except Exception as e:
                    return False, f"candidate_execution_failed (stage {stage}): {type(e).__name__}: {e}"
                finally:
                    costs["candidate"] = _add_costs(costs["candidate"], BudgetTracker.delta(snap, self.budget.snapshot()))
                snap = self.budget.snapshot()
                try:
                    base_runs = [await self._trial_optimize(base_objectives, self.state, seed, high_level_goal,
                                                            optimizer=opt, population=pop, stage=stage)
                                 for (pop, opt), seed in zip(base_runs, seeds)]
                    base_results = [self._validate_population(p) for p, _ in base_runs]
                    cand_results = [self._validate_population(p) for p, _ in cand_runs]
                except Exception as e:
                    return False, f"validation_failed (stage {stage}): {type(e).__name__}: {e}"
                finally:
                    costs["validation"] = _add_costs(costs["validation"], BudgetTracker.delta(snap, self.budget.snapshot()))

            validation.update({
                "baseline": stages[-1]["baseline"],
                "candidate": stages[-1]["candidate"],
                "baseline_mean": base_mean,
                "candidate_mean": cand_mean,
                "delta": delta,
                "min_improvement": min_improvement,
                "candidate_constraint_violation": violation,
                "details": {"baseline": [r.details for r in base_results], "candidate": [r.details for r in cand_results]},
            })
            if mode == "sequential":
                validation.update({"stages": stages, "stopped_at_stage": stage, "reject_margin": reject_margin})
            stage_note = f" at stage {stage}" if mode == "sequential" else ""
            if violation:
                accept, reason = False, "candidate_violates_validator_constraints"
            elif exhausted:
                accept, reason = False, f"budget_exceeded_during_validation: {why}"
            elif decision == "accept":
                accept, reason = True, f"validated improvement{stage_note}: delta={delta:.6g} (baseline {base_mean:.6g} -> candidate {cand_mean:.6g})"
            elif decision == "reject_budget":
                accept, reason = False, f"budget_insufficient_for_extended_validation (after stage {stage}, delta={delta:.6g}): {why_budget}"
            elif mode == "sequential" and delta <= reject_margin:
                accept, reason = False, f"clear_regression{stage_note}: delta={delta:.6g} (<= {reject_margin})"
            else:
                accept, reason = False, f"no_improvement{stage_note}: delta={delta:.6g} (required > 0 and >= {min_improvement})"

            if accept and self.validation_cfg.get("adopt_candidate_population", False):
                metrics = [r.metric for r in cand_results]
                best = int(np.argmax(metrics) if self.validator.higher_is_better else np.argmin(metrics))
                self.orch.current_population = cand_runs[best][0]
                validation["adopted_population"] = {"seed": seeds[best], "validation_metric": metrics[best],
                                                    "trial_iterations": stage}
            return accept, reason
        finally:
            random.setstate(py_state)
            np.random.set_state(np_state)
            self._cleanup_trial(registry_before, keep_scorers if accept else set(), trial_dir, keep_dir=accept and bool(keep_scorers))

    def _cleanup_trial(self, registry_before, keep_scorers, trial_dir: Path, keep_dir: bool) -> None:
        manager = ScorerManager()
        for name in set(list_scorers()) - registry_before - set(keep_scorers):
            manager.unregister_scorer(name)
        if not keep_dir and trial_dir.exists():
            shutil.rmtree(trial_dir, ignore_errors=True)

    # ------------------------------------------------------------------ commit
    def _commit(self, candidate_state: AcceptedState, target: str) -> None:
        candidate_state.version = self.state.version + 1
        self.state = candidate_state
        if target == "planning":
            self.orch.planner.set_strategy_guidance(self.state.planner_guidance)
        elif target == "optimization_workflow":
            optimizer_params = {k: v for k, v in self.state.workflow_params.items() if k not in LOOP_PARAM_SPECS}
            if optimizer_params:
                self.orch.optimizer.set_tunable_params(optimizer_params)
            for name in LOOP_PARAM_SPECS:
                if name in self.state.workflow_params:
                    self.orch.config.loop_config[name] = self.state.workflow_params[name]
        elif target in ("objective", "implementation"):
            # Re-applied after every scorer-creation phase; drop stale cached statistics now.
            self._clear_all_stat_caches(patched_objective_names(self.state))

    # ------------------------------------------------------------------ estimates & context
    def _estimate(self, target: Optional[str], include_judge: bool) -> Dict[str, float]:
        est = {"llm_calls": 0.0, "total_tokens_observed": 0.0, "oracle_evals": 0.0}
        estimates = self.cfg.get("estimates") or {}
        n_seeds = len(self.validation_cfg["seeds"])
        if include_judge:
            parse_retries = (self.cfg.get("judge") or {}).get("max_parse_retries", 1)
            est["llm_calls"] += 1 + parse_retries
            est["total_tokens_observed"] += estimates.get("judge_tokens", 8000)
        if target in (None, "planning"):
            est["llm_calls"] += 2
            est["total_tokens_observed"] += 2 * estimates.get("planner_call_tokens", 8000)
        optimizer = self.orch.optimizer
        overrides = self.validation_cfg.get("trial_optimizer_overrides") or {}
        if hasattr(optimizer, "estimate_evaluations"):
            per_trial = optimizer.estimate_evaluations(**overrides)
            pop_size = self.orch.current_population.size if self.orch.current_population else 0
            est["oracle_evals"] += 2 * n_seeds * (per_trial + pop_size * self._validation_cost_multiplier())
        if self.cfg.get("reserve_main_iteration", True) and self._main_iteration_costs:
            last = self._main_iteration_costs[-1]
            est["llm_calls"] += last["llm_calls"]
            est["total_tokens_observed"] += last["total_tokens_observed_lower_bound"]
            est["oracle_evals"] += last["oracle_evals"] or 0
        return est

    def _binding_name(self, obj: Objective) -> str:
        if obj.metadata.get("meta_controller_scorer_binding"):
            return obj.metadata["meta_controller_scorer_binding"]
        if obj.scorer is not None and get_scorer(obj.name) is obj.scorer:
            return obj.name
        return "custom" if obj.scorer is not None else "none"

    def _judge_context(self, iteration, max_iterations, analysis_result, objectives, high_level_goal) -> Dict[str, Any]:
        rebuild_ok, rebuild_why = self._rebuild_support()
        specs = self._tunable_specs()
        capabilities = {
            "allowed_targets": ", ".join(t for t in TARGETS if t in self.allowed_targets),
            "objective.add_from_registry types": ", ".join(self._allowed_objective_types()),
            "planning": "supported" if hasattr(self.orch.planner, "set_strategy_guidance") else "unsupported",
            "implementation.rebind_scorer": "supported",
            "implementation.sanitize_outputs": "supported for candidate-wise objectives",
            "implementation.rebuild_scorer": rebuild_why,
            "optimization_workflow": "supported" if specs else "unsupported",
            "max_ops_per_change": str(self.cfg.get("max_ops_per_change") or 3),
        }
        recent = []
        for r in self.records[-3:]:
            target = (r.get("decision") or {}).get("intervention_target")
            delta = (r.get("validation") or {}).get("delta")
            recent.append(f"iteration {r['iteration']}: target={target}, outcome={r['outcome']}, "
                          f"validation_delta={None if delta is None else round(delta, 6)}, reason={_truncate(r['reason'], 160)}")
        registered = []
        for name in list_scorers():
            meta = get_scorer_metadata(name) or {}
            registered.append({"name": name, "type": meta.get("type"), "description": _truncate(meta.get("description"), 300)})
        remaining = self.budget.remaining() if self.budget.caps else "no caps configured"
        try:
            diagnostics = self._diagnostics(objectives, specs)
        except Exception as e:  # diagnostics are advisory; never block the step
            diagnostics = {"error": f"{type(e).__name__}: {e}"}
        return {
            "diagnostics": diagnostics,
            "high_level_goal": high_level_goal,
            "iteration": iteration,
            "max_iterations": max_iterations,
            "analysis_report": _truncate(analysis_result.get("analysis_report"), 8000),
            "analyzer_should_stop": analysis_result.get("should_stop"),
            "analyzer_reasoning": _truncate(analysis_result.get("reasoning"), 600),
            "objectives": [
                {"name": o.name, "type": o.type, "optimization_direction": o.optimization_direction,
                 "weight": o.weight, "scorer": self._binding_name(o), "description": _truncate(o.description, 300)}
                for o in objectives
            ],
            "registered_scorers": registered,
            "accepted_state": self.state.to_dict(),
            "tunable_params": specs,
            "capabilities": capabilities,
            "recent_decisions": recent,
            "remaining_budget": remaining,
        }

    _RANGE = re.compile(r"in \[\s*(-?[0-9.]+)\s*,\s*(-?[0-9.]+)\s*\]")

    def _declared_range(self, obj: Objective):
        meta = get_scorer_metadata(self._binding_name(obj)) or {}
        for text in (meta.get("description"), obj.description):
            m = self._RANGE.search(text or "")
            if m:
                return [float(m.group(1)), float(m.group(2))]
        return None

    def _diagnostics(self, objectives: List[Objective], specs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Run diagnostics computed directly from the run state (independent of the Analyzer's report)."""
        population = self.orch.current_population
        out: Dict[str, Any] = {}
        if population is None or population.size == 0:
            return out
        score_stats = {}
        for obj in objectives:
            if obj.type == "population-wise":
                continue
            values = [c.scores.get(obj.name) for c in population.candidates]
            nums = [float(v) for v in values if v is not None and not isinstance(v, bool) and np.isfinite(float(v))]
            declared = self._declared_range(obj)
            entry = {"n": len(values), "failed_or_missing": len(values) - len(nums), "declared_range": declared}
            if nums:
                entry.update({"min": round(min(nums), 6), "max": round(max(nums), 6), "mean": round(float(np.mean(nums)), 6),
                              "std": round(float(np.std(nums)), 6)})
                if declared:
                    entry["n_outside_declared_range"] = sum(1 for v in nums if not declared[0] <= v <= declared[1])
            score_stats[obj.name] = entry
        out["objective_scores_current_population"] = score_stats

        history = {}
        km = self.orch.knowledge_manager
        for obj in objectives:
            if obj.type != "candidate-wise":
                continue
            best = []
            for it in sorted(getattr(km, "populations_by_iteration", {}))[-6:]:
                pop = km.get_population(it)
                vals = [c.scores.get(obj.name) for c in (pop.candidates if pop else [])]
                nums = [float(v) for v in vals if v is not None and not isinstance(v, bool)]
                if nums:
                    best.append([it, round(max(nums) if obj.optimization_direction == "maximize" else min(nums), 6)])
            history[obj.name] = best
        out["best_score_by_iteration_last6"] = history

        reps = [c.representation for c in population.candidates]
        if reps and all(isinstance(r, (list, tuple)) and r and all(isinstance(v, (int, float)) for v in r) for r in reps) \
                and len({len(r) for r in reps}) == 1:
            X = np.asarray(reps, dtype=float)
            dist = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
            out["population_diversity"] = {
                "per_dimension_std_mean": round(float(X.std(axis=0).mean()), 6),
                "per_dimension_std_min": round(float(X.std(axis=0).min()), 6),
                "mean_pairwise_distance": round(float(dist.sum() / max(1, len(X) * (len(X) - 1))), 6),
                "fraction_unique": round(len({tuple(np.round(r, 6)) for r in X}) / len(X), 3),
            }
        flags = {}
        for name, spec in specs.items():
            cur = spec.get("current")
            if isinstance(cur, (int, float)):
                flags[name] = {"current": cur, "default": spec.get("default"),
                               "at_lower_bound": cur <= spec["min"], "at_upper_bound": cur >= spec["max"]}
        out["tunable_parameter_status"] = flags
        stats = getattr(self.orch.optimizer, "last_run_stats", None)
        if stats:
            out["optimizer_reported_last_run"] = stats
        return out

    # ------------------------------------------------------------------ summary
    def summary(self) -> Dict[str, Any]:
        outcomes: Dict[str, int] = {}
        targets: Dict[str, Dict[str, int]] = {}
        for r in self.records:
            outcomes[r["outcome"]] = outcomes.get(r["outcome"], 0) + 1
            target = (r.get("decision") or {}).get("intervention_target")
            if target:
                targets.setdefault(target, {})
                targets[target][r["outcome"]] = targets[target].get(r["outcome"], 0) + 1
        attempted = sum(1 for r in self.records if r["outcome"] in ("accepted", "rejected"))
        return {
            "task_id": self.cfg.get("task_id"),
            "seed": self.cfg.get("seed"),
            "decisions": len(self.records),
            "outcomes": outcomes,
            "by_target": targets,
            "validated_candidates": attempted,
            "acceptance_rate": (outcomes.get("accepted", 0) / attempted) if attempted else None,
            "accepted_state": self.state.to_dict(),
            "controller_oracle_evals": {"trials": self.trial_evals, "validation": self.validation_evals,
                                        "validation_raw": self.validation_evals_raw,
                                        "validation_cost_multiplier": self._validation_cost_multiplier()},
            "budget": self.budget.report() if self.budget else None,
        }

    def finalize(self) -> None:
        path = Path(self.orch.output_dir) / "meta_controller_summary.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.summary(), f, indent=2, default=str)


def _build_judge(cfg: Dict[str, Any], orch) -> Optional[BaseJudge]:
    judge_cfg = cfg.get("judge") or {}
    if judge_cfg.get("type") == "random":
        from .judge import RandomTargetJudge
        return RandomTargetJudge(seed=int(judge_cfg.get("seed", cfg.get("seed") or 0)),
                                 max_ops=cfg.get("max_ops_per_change") or 1)
    if judge_cfg.get("type", "llm") != "llm":
        return None  # other judges are attached programmatically via MetaController.set_judge()
    planner_llm = orch.config.get_module_configs_by_type("planner")[0].llm_config
    model_name = judge_cfg.get("model_name") or (planner_llm.model_name if planner_llm else None)
    if not model_name:
        raise ValueError("meta_controller.judge.model_name is required (no planner model to fall back to)")
    return LLMJudge(
        model_name=model_name,
        models_file=judge_cfg.get("models_file") or (planner_llm.models_file if planner_llm else "llm_configs/models.yaml"),
        credentials_file=judge_cfg.get("credentials_file") or (planner_llm.credentials_file if planner_llm else "llm_configs/credentials.yaml"),
        prompt_version=judge_cfg.get("prompt_version", "v1"),
        diagnostics=judge_cfg.get("diagnostics"),
        max_ops_in_prompt=(cfg.get("max_ops_per_change") if judge_cfg.get("max_ops_in_prompt") else None),
        max_retries=judge_cfg.get("max_retries", 2),
        max_parse_retries=judge_cfg.get("max_parse_retries", 1),
        call_args=judge_cfg.get("call_args") or {},
    )


def build_meta_components(orch) -> Tuple[Optional[BudgetTracker], Optional[MetaController]]:
    """
    Build the opt-in budget guard and Meta-Controller for an orchestrator.

    Returns (budget_guard, controller): budget_guard is None unless loop_config["budget"] has caps;
    controller is None unless loop_config["meta_controller"]["enabled"] is True.
    """
    loop = orch.config.loop_config
    controller = None
    cfg = _deep_merge(DEFAULT_CONFIG, loop.get("meta_controller") or {})
    if cfg.get("enabled"):
        controller = MetaController(orch, cfg, judge=None, validator=get_validator(cfg.get("validator")))
        judge = _build_judge(cfg, orch)
        if judge is not None:
            controller.set_judge(judge)

    def clients():
        modules = [orch.planner, orch.scorer_creator, orch.optimizer, orch.analyzer, orch.knowledge_manager]
        out = [getattr(m, "llm_client", None) for m in modules]
        if controller is not None:
            out.extend(controller.extra_clients)
        return out

    def evals():
        main = getattr(orch.optimizer, "num_evaluations", None)
        if main is None:
            return None
        if controller is not None:
            return main + controller.trial_evals + controller.validation_evals
        return main

    tracker = BudgetTracker(loop.get("budget"), clients, evals)
    if controller is not None:
        controller.attach_budget(tracker)
    return (tracker if tracker.caps else None), controller
