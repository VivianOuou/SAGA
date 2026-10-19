"""SYNTHETIC numeric task 1 (robust design): proxy scorers. Self-contained (MCP module convention)."""

import json
from typing import List, Optional

import numpy as np

from .scorer_utils import BaseScorer, scorer


DIM = 8
CENTER = np.array([0.70, 0.62, 0.45, 0.55, 0.38, 0.60, 0.50, 0.42])
WIDTH = 0.35
TOLERANCE_STD = 0.08
MC_SAMPLES = 16
MC_SEED = 7


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


def _performance(X):
    bump = np.exp(-np.sum((X - CENTER) ** 2, axis=-1) / (2 * WIDTH ** 2))
    return np.where(X[..., 0] + X[..., 1] <= 1.0, bump, 0.0)


class Scorer(BaseScorer):
    @scorer(
        name="nominal_performance",
        population_wise=False,
        description="Nominal device performance in [0, 1], evaluated exactly at the design parameters (no manufacturing tolerance). Designs beyond the failure boundary x0 + x1 > 1.0 score 0. Higher is better.",
    )
    def score_nominal_performance(self, samples: List[str]) -> List[Optional[float]]:
        """Nominal performance of each design (JSON array of 8 floats in [0, 1])."""
        return [None if x is None else round(float(_performance(x)), 6) for x in _parse(samples)]

    @scorer(
        name="robust_performance_mc",
        population_wise=False,
        description="Monte-Carlo estimate (16 fixed tolerance samples, independent Gaussian deviation with std 0.08 per parameter) of the expected device performance in [0, 1] under manufacturing tolerances. Noisy but unbiased estimate. Higher is better.",
    )
    def score_robust_performance_mc(self, samples: List[str]) -> List[Optional[float]]:
        """Monte-Carlo expected performance under tolerance noise."""
        noise = np.random.default_rng(MC_SEED).normal(0.0, TOLERANCE_STD, size=(MC_SAMPLES, DIM))
        out = []
        for x in _parse(samples):
            out.append(None if x is None else round(float(np.mean(_performance(np.clip(x + noise, 0.0, 1.0)))), 6))
        return out

    @scorer(
        name="cliff_margin",
        population_wise=False,
        description="Signed Euclidean distance of the design to the failure boundary x0 + x1 = 1.0, in [-0.71, 0.71]. Positive values are inside the safe region; larger means safer.",
    )
    def score_cliff_margin(self, samples: List[str]) -> List[Optional[float]]:
        """Signed distance to the failure boundary."""
        return [None if x is None else round(float((1.0 - x[0] - x[1]) / np.sqrt(2.0)), 6) for x in _parse(samples)]

    @scorer(
        name="center_distance",
        population_wise=False,
        description="Normalized Euclidean distance of the design from the center point (0.5, ..., 0.5), in [0, 0.5].",
    )
    def score_center_distance(self, samples: List[str]) -> List[Optional[float]]:
        """Distance from the center of the design space."""
        return [None if x is None else round(float(np.linalg.norm(x - 0.5) / np.sqrt(DIM)), 6) for x in _parse(samples)]
