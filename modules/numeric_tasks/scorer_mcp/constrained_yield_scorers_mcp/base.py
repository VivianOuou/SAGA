"""SYNTHETIC numeric task 2 (constrained yield): proxy scorers. Self-contained (MCP module convention)."""

import json
from typing import List, Optional

import numpy as np

from .scorer_utils import BaseScorer, scorer


DIM = 6
A_NOMINAL = np.array([1.0, 0.8, 1.2, 0.6, 0.9, 1.1])
B = np.array([1.0, 1.5, 2.0, 0.5, 1.2, 1.8])
BUDGET = 0.15


def _parse(samples: List[str]):
    out = []
    for s in samples:
        try:
            x = np.asarray(json.loads(s), dtype=float)
        except Exception:
            out.append(None)
            continue
        out.append(np.clip(x, 0.0, 1.0) if x.shape == (DIM,) and np.all(np.isfinite(x)) else None)
    return out


def _yield(x):
    return float(np.sqrt(x) @ A_NOMINAL / A_NOMINAL.sum())


def _cost(x):
    return float((x ** 2) @ B / B.sum())


class Scorer(BaseScorer):
    @scorer(
        name="yield_estimate",
        population_wise=False,
        description="Expected production yield in [0, 1] under nominal market conditions (weighted sum of square roots of the allocation levels, normalized). Higher is better.",
    )
    def score_yield_estimate(self, samples: List[str]) -> List[Optional[float]]:
        """Nominal yield of each allocation (JSON array of 6 floats in [0, 1])."""
        return [None if x is None else round(_yield(x), 6) for x in _parse(samples)]

    @scorer(
        name="production_cost",
        population_wise=False,
        description="Normalized production cost in [0, 1] (weighted sum of squared allocation levels). The hard budget is cost <= 0.15. Lower is cheaper.",
    )
    def score_production_cost(self, samples: List[str]) -> List[Optional[float]]:
        """Normalized production cost."""
        return [None if x is None else round(_cost(x), 6) for x in _parse(samples)]

    @scorer(
        name="within_cost_budget",
        population_wise=False,
        description="Filter: passes (1.0) if the normalized production cost is <= 0.15 (the hard budget), fails (0.0) otherwise.",
    )
    def score_within_cost_budget(self, samples: List[str]) -> List[Optional[float]]:
        """Budget feasibility filter."""
        return [None if x is None else (1.0 if _cost(x) <= BUDGET else 0.0) for x in _parse(samples)]

    @scorer(
        name="cost_budget_slack",
        population_wise=False,
        description="Budget slack 0.15 - cost, in [-0.85, 0.15]. Negative values mean the design is over budget. Larger means more slack.",
    )
    def score_cost_budget_slack(self, samples: List[str]) -> List[Optional[float]]:
        """Remaining budget."""
        return [None if x is None else round(BUDGET - _cost(x), 6) for x in _parse(samples)]

    @scorer(
        name="yield_per_unit_cost",
        population_wise=False,
        description="Production efficiency: nominal yield divided by (cost + 0.05). Higher means more yield per unit cost.",
    )
    def score_yield_per_unit_cost(self, samples: List[str]) -> List[Optional[float]]:
        """Yield per unit cost."""
        return [None if x is None else round(_yield(x) / (_cost(x) + 0.05), 6) for x in _parse(samples)]
