"""
Judges propose (never accept) interventions.

`BaseJudge.decide(context)` is the small replaceable interface. `LLMJudge` is a plain LLM judge
built on the project's LLMClient / models.yaml configuration. No other judge type is implemented.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..utils.llm import create_client


@dataclass
class JudgeOutput:
    raw: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0


class BaseJudge(ABC):
    judge_type = "base"

    @property
    def llm_clients(self) -> List[Any]:
        """LLM clients owned by this judge (counted in the budget)."""
        return []

    def describe(self) -> Dict[str, Any]:
        return {"judge_type": self.judge_type}

    @abstractmethod
    async def decide(self, context: Dict[str, Any]) -> JudgeOutput:
        """Return a raw decision dict (validated by the controller) or an error."""


JUDGE_SYSTEM_PROMPT = """You are the meta-controller judge of an iterative scientific optimization system (SAGA). Each iteration runs Planner -> Implementer (maps objectives to scorer code) -> Optimizer -> Analyzer. After each Analyzer report you choose AT MOST ONE bounded intervention for the following iterations.

Your proposal is executed in isolation and is accepted only if a fixed, independent validator (which you cannot see or change) shows an improvement over the currently accepted state; otherwise it is discarded. Speculative or unnecessary changes waste the shared budget.

Keep three things separate (they may differ):
- failure_location: where the shortfall shows up: "objective", "planning", "implementation", "optimization_workflow", "analysis", "none" or "unknown".
- root_cause_hypothesis: your best explanation; say so when you are unsure.
- intervention_target: what is most worth changing next. Example: a failure that shows up in implementation may be best fixed by planning.

Targets and the exact `proposed_change` schema:
1. "objective": directly edit the objective set the optimizer uses (persists until replaced).
   {"ops": [{"op": "set_weight", "name": <current objective>, "weight": <0.05-20>},
            {"op": "drop", "name": <current objective>},
            {"op": "add_from_registry", "name": <registered scorer>, "optimization_direction": "maximize"|"minimize", "weight": <optional>}]}  (1-3 ops)
2. "planning": persistent strategy guidance shown to the Planner in later iterations; the Planner still chooses the objectives.
   {"guidance": "<20-1500 characters>", "mode": "replace"|"append"}
3. "implementation": fix how an objective is computed without changing what it means.
   {"objective_name": <current objective>, "action": "rebind_scorer", "scorer_name": <registered scorer of the same type>}
   {"objective_name": <current objective>, "action": "sanitize_outputs", "valid_range": [low, high]}  (non-finite or out-of-range outputs become failed evaluations)
   {"objective_name": <current objective>, "action": "rebuild_scorer", "instructions": "<what to fix>"}  (only if listed as supported)
4. "optimization_workflow": change 1-3 of the listed tunable parameters within their bounds.
   {"params": {"<parameter>": <value>}}
5. "no_change": keep the accepted state; the normal loop simply continues (this is NOT a stop decision). proposed_change must be null.

Rules:
- Ground the rationale in observable evidence from the inputs (quote the numbers you rely on).
- expected_benefit is a hypothesis, not a measurement.
- validation_plan is only a suggestion; the acceptance test is fixed in advance and cannot be changed by you.
- Use only objective, scorer and parameter names that appear in the inputs.
- confidence is optional: your self-reported, uncalibrated confidence in [0, 1].

Output: brief reasoning, then exactly one JSON object inside <decision>...</decision> with the keys failure_location, root_cause_hypothesis, intervention_target, rationale, proposed_change, expected_benefit, validation_plan, confidence."""


JUDGE_SYSTEM_PROMPT_V2_ADDENDUM = """

Important context for prompt version 2:
- The Analyzer is instructed by design to recommend objective-level changes only (it may not suggest optimizer or implementation changes). Its recommendations are therefore NOT evidence that the problem lies in the objectives.
- A "Run diagnostics" section is computed directly from the run state, independently of the Analyzer: objective score statistics (including values outside the declared range), best score per iteration, population diversity, tunable-parameter status (current value, default, at bounds) and optimizer-reported statistics. Use it as primary evidence.
- Before choosing, assess every target in one sentence each, in a "target_assessment" object with the keys objective, planning, implementation, optimization_workflow, no_change. Then choose the single target most likely to fix the observed problem.

Output keys for version 2: failure_location, root_cause_hypothesis, intervention_target, rationale, proposed_change, expected_benefit, validation_plan, confidence, target_assessment."""


_V2_HEADER = "\n\nImportant context for prompt version 2:\n"
_V2_ANALYZER = ("- The Analyzer is instructed by design to recommend objective-level changes only (it may not suggest optimizer "
                "or implementation changes). Its recommendations are therefore NOT evidence that the problem lies in the objectives.\n")
_DIAG = ('- A "Run diagnostics" section is computed directly from the run state, independently of the Analyzer: objective score '
         "statistics (including values outside the declared range), best score per iteration, population diversity, "
         "tunable-parameter status (current value, default, at bounds) and optimizer-reported statistics. Use it as primary evidence.\n")
_V2_ASSESS = ('- Before choosing, assess every target in one sentence each, in a "target_assessment" object with the keys objective, '
              "planning, implementation, optimization_workflow, no_change. Then choose the single target most likely to fix the observed problem.\n"
              "\nOutput keys for version 2: failure_location, root_cause_hypothesis, intervention_target, rationale, proposed_change, "
              "expected_benefit, validation_plan, confidence, target_assessment.")


def build_system_prompt(prompt_version: str = "v1", diagnostics: bool = False, max_ops: Optional[int] = None) -> str:
    """Compose the judge system prompt. v1 without diagnostics/max_ops is the original text byte for byte;
    v2 with diagnostics and no max_ops is the v2b (arm D) text byte for byte."""
    base = JUDGE_SYSTEM_PROMPT
    if max_ops is not None:
        ops = "exactly 1 op" if max_ops == 1 else f"1-{max_ops} ops"
        params = "exactly 1" if max_ops == 1 else f"1-{max_ops}"
        base = base.replace("  (1-3 ops)", f"  ({ops}; more are rejected as invalid)")
        base = base.replace("change 1-3 of the listed tunable parameters", f"change {params} of the listed tunable parameters")
    if prompt_version == "v2":
        return base + _V2_HEADER + _V2_ANALYZER + (_DIAG if diagnostics else "") + _V2_ASSESS
    if diagnostics:
        return base + "\n\nAdditional context:\n" + _DIAG.rstrip("\n")
    return base


def _fmt_objectives(objectives: List[Dict[str, Any]]) -> str:
    lines = []
    for o in objectives:
        lines.append(
            f"- {o['name']} | type={o.get('type')} | direction={o.get('optimization_direction')} | "
            f"weight={o.get('weight')} | scorer={o.get('scorer')} | {o.get('description', '')}"
        )
    return "\n".join(lines) or "(none)"


def render_judge_prompt(ctx: Dict[str, Any], prompt_version: str = "v1", diagnostics: Optional[bool] = None) -> str:
    if diagnostics is None:
        diagnostics = prompt_version == "v2"
    sections = [
        f"# Goal\n{ctx['high_level_goal']}",
        f"# Iteration\nIteration {ctx['iteration']} of at most {ctx['max_iterations']} just finished. "
        f"An accepted intervention takes effect from iteration {ctx['iteration'] + 1}.",
        f"# Analyzer report (iteration {ctx['iteration']})\n{ctx['analysis_report']}\n\n"
        f"Analyzer stop decision: {ctx['analyzer_should_stop']} - {ctx.get('analyzer_reasoning', '')}",
        f"# Objectives used in iteration {ctx['iteration']}\n{_fmt_objectives(ctx['objectives'])}",
        "# Registered scorers (usable for add_from_registry / rebind_scorer)\n"
        + ("\n".join(f"- {s['name']} | type={s['type']} | {s['description']}" for s in ctx["registered_scorers"]) or "(none)"),
        f"# Currently accepted interventions (state version {ctx['accepted_state']['version']})\n"
        + json.dumps(ctx["accepted_state"], indent=1),
        "# Tunable optimization/workflow parameters\n"
        + ("\n".join(
            f"- {name}: current={spec.get('current')}, bounds=[{spec['min']}, {spec['max']}], type={spec['type']} - {spec.get('description', '')}"
            for name, spec in ctx["tunable_params"].items()) or "(none: optimization_workflow is unsupported)"),
        "# Supported actions\n" + "\n".join(f"- {k}: {v}" for k, v in ctx["capabilities"].items()),
        "# Recent meta-controller decisions\n"
        + ("\n".join(f"- {h}" for h in ctx["recent_decisions"]) or "(none yet)"),
        "# Remaining budget\n" + json.dumps(ctx["remaining_budget"]),
    ]
    if diagnostics:
        sections.insert(4, "# Run diagnostics (computed by the meta-controller, independent of the Analyzer)\n"
                        + json.dumps(ctx.get("diagnostics", {}), indent=1))
    return "\n\n".join(sections)


def extract_decision_json(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    matches = re.findall(r"<decision>(.*?)</decision>", text or "", re.DOTALL)
    if not matches:
        return None, "no <decision>...</decision> block found"
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*|\s*```$", "", body)
    try:
        value = json.loads(body)
    except json.JSONDecodeError as e:
        return None, f"invalid JSON in <decision>: {e}"
    if not isinstance(value, dict):
        return None, "<decision> must contain a JSON object"
    return value, None


SAFE_CALL_ARGS = {"temperature", "top_p", "max_tokens", "max_completion_tokens", "reasoning_effort", "seed"}


class LLMJudge(BaseJudge):
    judge_type = "llm"

    def __init__(
        self,
        model_name: str,
        models_file: str = "llm_configs/models.yaml",
        credentials_file: str = "llm_configs/credentials.yaml",
        max_retries: int = 2,
        retry_delay: float = 1.0,
        max_parse_retries: int = 1,
        call_args: Optional[Dict[str, Any]] = None,
        client=None,
        prompt_version: str = "v1",
        diagnostics: Optional[bool] = None,
        max_ops_in_prompt: Optional[int] = None,
    ):
        if prompt_version not in ("v1", "v2"):
            raise ValueError(f"unknown judge prompt_version '{prompt_version}'")
        self.prompt_version = prompt_version
        self.diagnostics = (prompt_version == "v2") if diagnostics is None else bool(diagnostics)
        self.max_ops_in_prompt = max_ops_in_prompt
        self.model_name = model_name
        self.max_parse_retries = max_parse_retries
        self.call_args = dict(call_args or {})
        self.client = client or create_client(
            model_name=model_name,
            models_file=models_file,
            credentials_file=credentials_file,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

    @property
    def llm_clients(self) -> List[Any]:
        return [self.client]

    def describe(self) -> Dict[str, Any]:
        cfg = getattr(self.client, "config", None)
        return {
            "judge_type": self.judge_type,
            "model_name": self.model_name,
            "provider": getattr(cfg, "provider", None),
            "model": getattr(cfg, "model", None),
            "call_args": {k: v for k, v in self.call_args.items() if k in SAFE_CALL_ARGS},
            "max_parse_retries": self.max_parse_retries,
            "prompt_version": self.prompt_version,
            "diagnostics": self.diagnostics,
            "max_ops_in_prompt": self.max_ops_in_prompt,
        }

    async def decide(self, context: Dict[str, Any]) -> JudgeOutput:
        system = build_system_prompt(self.prompt_version, self.diagnostics, self.max_ops_in_prompt)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": render_judge_prompt(context, self.prompt_version, self.diagnostics)},
        ]
        last_error = None
        text = None
        for attempt in range(1, self.max_parse_retries + 2):
            try:
                response = await self.client.call_async(messages, **self.call_args)
            except Exception as e:  # provider/auth/network failure after LLMClient retries
                return JudgeOutput(raw_text=text, error=f"judge_call_failed: {type(e).__name__}: {e}", attempts=attempt)
            text = response.get("content") or ""
            raw, last_error = extract_decision_json(text)
            if raw is not None:
                return JudgeOutput(raw=raw, raw_text=text, attempts=attempt)
            messages = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": f"Your output could not be parsed ({last_error}). Reply with the <decision> JSON object only."},
            ]
        return JudgeOutput(raw_text=text, error=f"judge_output_unparseable: {last_error}", attempts=self.max_parse_retries + 1)


class RandomTargetJudge(BaseJudge):
    """
    Control judge (no LLM): picks an intervention target uniformly at random from the allowed targets
    and a random valid, bounded change for it. Used to separate the value of *choosing* the target
    from the value of the validation gate. Not a mock: it is a real experimental control.
    """

    judge_type = "random_target_control"
    _RANGE = re.compile(r"in \[\s*(-?[0-9.]+)\s*,\s*(-?[0-9.]+)\s*\]")

    def __init__(self, seed: int = 0, max_ops: int = 1):
        import random as _random

        self.seed = seed
        self.max_ops = max(1, int(max_ops))
        self.rng = _random.Random(seed)

    def describe(self) -> Dict[str, Any]:
        return {"judge_type": self.judge_type, "seed": self.seed, "max_ops": self.max_ops}

    def _declared_range(self, description: str):
        m = self._RANGE.search(description or "")
        return [float(m.group(1)), float(m.group(2))] if m else [0.0, 1.0]

    def _change(self, target: str, ctx: Dict[str, Any]):
        rng = self.rng
        objectives = [o for o in ctx["objectives"] if o.get("type") != "filter"]
        names = {o["name"] for o in ctx["objectives"]}
        allowed_types = [t.strip() for t in ctx["capabilities"].get("objective.add_from_registry types", "candidate-wise").split(",")]
        addable = [s for s in ctx["registered_scorers"] if s["name"] not in names and s.get("type") in allowed_types]
        if target == "objective":
            kinds = ["set_weight"] + (["drop"] if len(objectives) > 1 else []) + (["add_from_registry"] if addable else [])
            kind = rng.choice(kinds)
            if kind == "set_weight":
                op = {"op": "set_weight", "name": rng.choice(objectives)["name"], "weight": round(2 ** rng.uniform(-2, 2), 3)}
            elif kind == "drop":
                op = {"op": "drop", "name": rng.choice(objectives)["name"]}
            else:
                s = rng.choice(addable)
                op = {"op": "add_from_registry", "name": s["name"], "weight": round(2 ** rng.uniform(-2, 2), 3)}
                if s.get("type") != "filter":
                    op["optimization_direction"] = rng.choice(["maximize", "minimize"])
            return {"ops": [op]}
        if target == "planning":
            focus = rng.choice(objectives)["name"] if objectives else "the main objective"
            other = rng.choice(ctx["registered_scorers"])["name"] if ctx["registered_scorers"] else focus
            return {"guidance": f"In the next iterations prioritize '{focus}' and consider also using '{other}'.", "mode": "replace"}
        if target == "implementation":
            cand = [o for o in objectives if o.get("type") == "candidate-wise"]
            if not cand:
                return None
            obj = rng.choice(cand)
            others = [s["name"] for s in ctx["registered_scorers"] if s.get("type") == obj.get("type") and s["name"] != obj.get("scorer")]
            actions = ["sanitize_outputs"] + (["rebind_scorer"] if others else [])
            if rng.choice(actions) == "rebind_scorer":
                return {"objective_name": obj["name"], "action": "rebind_scorer", "scorer_name": rng.choice(others)}
            return {"objective_name": obj["name"], "action": "sanitize_outputs", "valid_range": self._declared_range(obj.get("description"))}
        if target == "optimization_workflow":
            specs = ctx["tunable_params"]
            if not specs:
                return None
            name = rng.choice(sorted(specs))
            spec = specs[name]
            value = rng.uniform(spec["min"], spec["max"])
            return {"params": {name: int(round(value)) if spec["type"] == "int" else round(value, 4)}}
        return None

    async def decide(self, context: Dict[str, Any]) -> JudgeOutput:
        targets = [t.strip() for t in context["capabilities"]["allowed_targets"].split(",") if t.strip()]
        target = self.rng.choice(targets)
        change = None if target == "no_change" else self._change(target, context)
        if target != "no_change" and change is None:
            target = "no_change"
        raw = {
            "failure_location": "unknown",
            "root_cause_hypothesis": "random-target control: no diagnosis is made",
            "intervention_target": target,
            "rationale": "random-target control (uniform over allowed targets, random valid bounded change)",
            "proposed_change": change,
            "expected_benefit": "none expected (control condition)",
            "validation_plan": "standard fixed validation",
        }
        return JudgeOutput(raw=raw, raw_text=json.dumps(raw), attempts=1)
