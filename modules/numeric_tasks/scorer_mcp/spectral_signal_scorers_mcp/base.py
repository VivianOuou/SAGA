"""
SYNTHETIC numeric task 3 (spectral signal design): proxy scorers. Self-contained (MCP module convention).

Benchmark design note: `smoothness` contains a DELIBERATE implementation bug (sign error in the
exponent, so it grows with roughness and exceeds its documented [0, 1] range). It stands in for a
faulty generated scorer and is used to test implementation-level interventions. `smoothness_v2` is
a correct implementation. See modules/numeric_tasks/README.md.
"""

import json
from typing import List, Optional

import numpy as np

from .scorer_utils import BaseScorer, scorer


DIM = 12
_K = np.arange(DIM)
TARGET_SIGNAL = 0.5 + 0.25 * np.sin(2 * np.pi * _K / 12) + 0.12 * np.cos(2 * np.pi * 2 * _K / 12 + 0.4)
TARGET_SPECTRUM = np.abs(np.fft.rfft(TARGET_SIGNAL))[:5] / 12
SE_SCALE = 0.01
ROUGHNESS_SCALE = 2.0


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


def _roughness(x):
    return float(np.sum((x[2:] - 2 * x[1:-1] + x[:-2]) ** 2))


class Scorer(BaseScorer):
    @scorer(
        name="spectrum_match",
        population_wise=False,
        description="Match between the signal's low-frequency magnitude spectrum (DC and harmonics 1-4) and the target spectrum, in [0, 1] (exp(-squared error / 0.01)). 1 means a perfect match. Higher is better.",
    )
    def score_spectrum_match(self, samples: List[str]) -> List[Optional[float]]:
        """Spectral match of each 12-sample signal (JSON array of floats in [0, 1])."""
        out = []
        for x in _parse(samples):
            if x is None:
                out.append(None)
                continue
            se = float(np.sum((np.abs(np.fft.rfft(x))[:5] / 12 - TARGET_SPECTRUM) ** 2))
            out.append(round(float(np.exp(-se / SE_SCALE)), 6))
        return out

    @scorer(
        name="smoothness",
        population_wise=False,
        description="Signal smoothness in [0, 1]; higher means smoother (fewer abrupt changes between consecutive samples).",
    )
    def score_smoothness(self, samples: List[str]) -> List[Optional[float]]:
        """Smoothness of each signal."""
        # Deliberate benchmark bug: the exponent sign is wrong (see module docstring).
        return [None if x is None else round(float(np.exp(_roughness(x) / ROUGHNESS_SCALE)), 6) for x in _parse(samples)]

    @scorer(
        name="smoothness_v2",
        population_wise=False,
        description="Signal smoothness in [0, 1] computed as exp(-sum of squared second differences / 2.0); 1 means perfectly linear (smoothest). Higher is better.",
    )
    def score_smoothness_v2(self, samples: List[str]) -> List[Optional[float]]:
        """Smoothness of each signal (second-difference based)."""
        return [None if x is None else round(float(np.exp(-_roughness(x) / ROUGHNESS_SCALE)), 6) for x in _parse(samples)]

    @scorer(
        name="signal_mean_level",
        population_wise=False,
        description="Mean value of the 12 signal samples, in [0, 1].",
    )
    def score_signal_mean_level(self, samples: List[str]) -> List[Optional[float]]:
        """Mean level of each signal."""
        return [None if x is None else round(float(np.mean(x)), 6) for x in _parse(samples)]
