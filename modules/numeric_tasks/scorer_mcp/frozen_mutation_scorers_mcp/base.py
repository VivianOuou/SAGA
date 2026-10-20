"""SYNTHETIC v3 HELD-OUT task `frozen_mutation`: proxy scorers. Self-contained (MCP module convention).

The scorers here are correct; the planted problem of this task is the optimizer configuration
(see modules/numeric_tasks/README.md). Performance is an anisotropic, rotated (non-separable) bump."""

import json
from typing import List, Optional

import numpy as np

from .scorer_utils import BaseScorer, scorer

DIM = 8
CENTER = np.array([0.38, 0.66, 0.52, 0.29, 0.61, 0.45, 0.70, 0.34])
_Q, _ = np.linalg.qr(np.random.default_rng(42).normal(size=(DIM, DIM)))
_WIDTHS = np.array([0.06, 0.08, 0.10, 0.14, 0.2, 0.3, 0.4, 0.5])
_M = _Q @ np.diag(1.0 / _WIDTHS ** 2) @ _Q.T


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


class Scorer(BaseScorer):
    @scorer(name="performance", population_wise=False,
            description="Device performance in [0, 1] at the design point. Higher is better.")
    def score_performance(self, samples: List[str]) -> List[Optional[float]]:
        """Performance of each design (JSON array of 8 floats in [0, 1])."""
        out = []
        for x in _parse(samples):
            out.append(None if x is None else round(float(np.exp(-0.5 * (x - CENTER) @ _M @ (x - CENTER))), 6))
        return out

    @scorer(name="parameter_spread", population_wise=False,
            description="Standard deviation of the 8 design parameters, in [0, 0.5].")
    def score_parameter_spread(self, samples: List[str]) -> List[Optional[float]]:
        """Spread of the design parameters."""
        return [None if x is None else round(float(np.std(x)), 6) for x in _parse(samples)]

    @scorer(name="distance_from_center", population_wise=False,
            description="Normalized Euclidean distance of the design from the center point (0.5, ..., 0.5), in [0, 0.5].")
    def score_distance_from_center(self, samples: List[str]) -> List[Optional[float]]:
        """Distance from the center of the design space."""
        return [None if x is None else round(float(np.linalg.norm(x - 0.5) / np.sqrt(DIM)), 6) for x in _parse(samples)]
