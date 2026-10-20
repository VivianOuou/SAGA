"""
SYNTHETIC numeric tasks for smoke tests and the small Meta-Controller A/B pilot.

Each task couples (a) a natural-language goal for the Planner/Analyzer, (b) an MCP module of proxy
scorers (some aligned, some misleading, one deliberately buggy), and (c) an independent validator
with disjoint validation / test splits. Success thresholds are fixed by calibration before any A/B run
(exps/meta_controller/calibrate_tasks.py -> exps/meta_controller/task_thresholds.json).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


@dataclass
class NumericTask:
    task_id: str
    dim: int
    goal: str
    context: str
    mcp_module: str
    initial_objectives: Dict[str, Optional[str]]
    validator: str
    design_note: str = ""
    suite: str = "v1"
    # Applied identically to every arm (task-defined starting configuration).
    optimizer_overrides: Dict[str, float] = field(default_factory=dict)
    loop_overrides: Dict[str, float] = field(default_factory=dict)
    # Known by construction (v2): the intervention target that fixes the planted problem.
    best_target: Optional[str] = None


TASKS: Dict[str, NumericTask] = {
    "robust_design": NumericTask(
        task_id="robust_design",
        dim=8,
        goal=("Design 8-dimensional parameter vectors (each parameter in [0, 1]) for a device whose performance must be "
              "robust to manufacturing tolerances: every parameter deviates from its design value by independent Gaussian "
              "noise with std 0.08. Designs that cross the failure boundary (x0 + x1 > 1.0) have zero performance. "
              "Maximize the expected performance under these tolerances."),
        context="Candidates are JSON arrays of 8 floats in [0, 1]. The optimizer keeps values inside [0, 1].",
        mcp_module="modules/numeric_tasks/scorer_mcp/robust_design_scorers_mcp",
        initial_objectives={"nominal_performance": "maximize"},
        validator="robust_design_truth",
        design_note="Nominal optimum sits on the failure boundary; robust optimum is set back from it.",
    ),
    "constrained_yield": NumericTask(
        task_id="constrained_yield",
        dim=6,
        goal=("Choose 6 resource allocation levels (each in [0, 1]) that maximize the expected production yield across "
              "uncertain market scenarios, subject to a hard budget: the normalized production cost must not exceed 0.15. "
              "Over-budget designs are worthless."),
        context="Candidates are JSON arrays of 6 floats in [0, 1]. The optimizer keeps values inside [0, 1].",
        mcp_module="modules/numeric_tasks/scorer_mcp/constrained_yield_scorers_mcp",
        initial_objectives={"yield_estimate": "maximize", "production_cost": "minimize"},
        validator="constrained_yield_truth",
        design_note="Initial yield-vs-cost trade-off does not enforce the hard budget; a feasibility filter exists.",
    ),
    "spectral_signal": NumericTask(
        task_id="spectral_signal",
        dim=12,
        goal=("Design a 12-sample control signal (values in [0, 1]) whose low-frequency magnitude spectrum (DC and the first "
              "four harmonics) matches a target spectrum, while being smooth (small second differences) because the actuator "
              "cannot follow abrupt changes."),
        context="Candidates are JSON arrays of 12 floats in [0, 1]. The optimizer keeps values inside [0, 1].",
        mcp_module="modules/numeric_tasks/scorer_mcp/spectral_signal_scorers_mcp",
        initial_objectives={"spectrum_match": "maximize", "smoothness": "maximize"},
        validator="spectral_signal_truth",
        design_note="Initial 'smoothness' scorer has a planted sign bug (values > 1 that grow with roughness).",
    ),
}

_V2_CONTEXT = "Candidates are JSON arrays of 8 floats in [0, 1]. The optimizer keeps values inside [0, 1]."

TASKS.update({
    "stagnant_search": NumericTask(
        task_id="stagnant_search", dim=8, suite="v2",
        goal="Design 8-dimensional parameter vectors (each parameter in [0, 1]) that maximize device performance.",
        context=_V2_CONTEXT,
        mcp_module="modules/numeric_tasks/scorer_mcp/stagnant_search_scorers_mcp",
        initial_objectives={"performance": "maximize"},
        validator="stagnant_search_truth",
        optimizer_overrides={"mutation_sigma": 0.005, "mutation_prob": 0.05, "crossover_rate": 0.0},
        best_target="optimization_workflow",
        design_note="Scorers are correct; the optimizer starts misconfigured (almost no variation) and stagnates.",
    ),
    "overflow_scorer": NumericTask(
        task_id="overflow_scorer", dim=8, suite="v2",
        goal="Design 8-dimensional parameter vectors (each parameter in [0, 1]) that maximize the design quality.",
        context=_V2_CONTEXT,
        mcp_module="modules/numeric_tasks/scorer_mcp/overflow_scorer_scorers_mcp",
        initial_objectives={"quality_score": "maximize"},
        validator="overflow_scorer_truth",
        best_target="implementation",
        design_note="quality_score overflows (values >> 1) when any parameter > 0.95; no alternative scorer exists.",
    ),
    "noisy_search": NumericTask(
        task_id="noisy_search", dim=8, suite="v2",
        goal="Design 8-dimensional parameter vectors (each parameter in [0, 1]) that maximize device performance.",
        context=_V2_CONTEXT,
        mcp_module="modules/numeric_tasks/scorer_mcp/noisy_search_scorers_mcp",
        initial_objectives={"performance": "maximize"},
        validator="noisy_search_truth",
        optimizer_overrides={"mutation_sigma": 0.5, "mutation_prob": 1.0},
        best_target="optimization_workflow",
        design_note="Scorers are correct; the optimizer starts misconfigured (huge mutations) and behaves like random search.",
    ),
    "underflow_cost": NumericTask(
        task_id="underflow_cost", dim=8, suite="v2b_holdout",
        goal="Design 8-dimensional parameter vectors (each parameter in [0, 1]) that minimize the design cost.",
        context=_V2_CONTEXT,
        mcp_module="modules/numeric_tasks/scorer_mcp/underflow_cost_scorers_mcp",
        initial_objectives={"design_cost": "minimize"},
        validator="underflow_cost_truth",
        best_target="implementation",
        design_note="HELD-OUT. design_cost underflows (huge negative values) when any parameter < 0.05; no alternative scorer.",
    ),
    "frozen_mutation": NumericTask(
        task_id="frozen_mutation", dim=8, suite="v3_holdout",
        goal="Design 8-dimensional parameter vectors (each parameter in [0, 1]) that maximize device performance.",
        context=_V2_CONTEXT,
        mcp_module="modules/numeric_tasks/scorer_mcp/frozen_mutation_scorers_mcp",
        initial_objectives={"performance": "maximize"},
        validator="frozen_mutation_truth",
        optimizer_overrides={"mutation_prob": 0.0},
        best_target="optimization_workflow",
        design_note="HELD-OUT (v3). Optimizer starts with mutation_prob=0 (crossover only) on a non-separable bump.",
    ),
    "offset_scorer": NumericTask(
        task_id="offset_scorer", dim=8, suite="v3_holdout",
        goal="Design 8-dimensional parameter vectors (each parameter in [0, 1]) that maximize the design quality.",
        context=_V2_CONTEXT,
        mcp_module="modules/numeric_tasks/scorer_mcp/offset_scorer_scorers_mcp",
        initial_objectives={"quality_score": "maximize"},
        validator="offset_scorer_truth",
        best_target="implementation",
        design_note="HELD-OUT (v3). quality_score returns 1 + 0.9*x3 (moderately > 1) when x3 > 0.85; no alternative scorer.",
    ),
})

THRESHOLDS_FILE = Path(__file__).resolve().parents[2] / "exps" / "meta_controller" / "task_thresholds.json"


def load_success_thresholds() -> Dict[str, float]:
    if not THRESHOLDS_FILE.exists():
        return {}
    with open(THRESHOLDS_FILE) as f:
        return {k: v["success_threshold"] for k, v in json.load(f).items()}


def scorer_catalog_text(scorer_names: List[str], metadata_fn) -> str:
    lines = ["Available computational scorers (objectives must use these exact names; in this setup no new scorers "
             "can be implemented):"]
    for name in sorted(scorer_names):
        meta = metadata_fn(name) or {}
        lines.append(f"- {name} ({meta.get('type', 'candidate-wise')}): {meta.get('description', '')}")
    return "\n".join(lines)


def initial_population_vectors(dim: int, size: int, seed: int) -> List[List[float]]:
    rng = np.random.default_rng(10_000 + seed)
    return [[round(float(v), 6) for v in row] for row in rng.random((size, dim))]
