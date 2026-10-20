"""
Independent validators (ground truth) for the SYNTHETIC numeric tasks.

These are written separately from the scorer MCP modules on purpose: a bug in a scorer must not
propagate into the validator. Each validator recomputes quality from raw vectors and never reads
candidate scores. Splits use independent random draws:
    validation  -> Meta-Controller accept/reject only
    test        -> final A/B reporting only (never used for selection)
    calibration -> setting success thresholds before any A/B run
Population metric = mean true quality of the first k candidates in the population's own order, i.e. the
candidates the system itself ranks highest (SAGA optimizers return populations sorted by their fitness).
This measures whether the system's objectives select truly good candidates; rescaling or redefining an
objective cannot inflate it because quality is recomputed here for whatever the system ranks first.
"""

import json
from typing import Any, Dict, List, Optional

import numpy as np

from scileo_agent.meta_controller.validators import BaseValidator, ValidationResult, register_validator


SPLIT_SEEDS = {"validation": 1001, "test": 2002, "calibration": 3003}
SPLIT_DRAWS = {"validation": 48, "test": 256, "calibration": 64}
TOP_K = 5


def _parse_vectors(representations: List[Any], dim: int):
    X = np.zeros((len(representations), dim))
    valid = np.zeros(len(representations), dtype=bool)
    for i, rep in enumerate(representations):
        try:
            x = np.asarray(json.loads(rep) if isinstance(rep, str) else rep, dtype=float)
        except Exception:
            continue
        if x.shape == (dim,) and np.all(np.isfinite(x)):
            X[i] = np.clip(x, 0.0, 1.0)
            valid[i] = True
    return X, valid


class NumericTaskValidator(BaseValidator):
    dim: int = 0

    def __init__(self, top_k: int = TOP_K):
        self.top_k = top_k

    def quality(self, X: np.ndarray, split: str) -> np.ndarray:
        raise NotImplementedError

    def evaluate(self, representations: List[Any], split: str = "validation") -> ValidationResult:
        if split not in SPLIT_SEEDS:
            raise ValueError(f"unknown split '{split}'")
        X, valid = _parse_vectors(representations, self.dim)
        q = np.zeros(len(representations))
        if valid.any():
            q[valid] = self.quality(X[valid], split)
        top_system = q[: self.top_k]
        top_oracle = np.sort(q)[::-1][: self.top_k]
        return ValidationResult(
            metric=float(np.mean(top_system)) if len(top_system) else 0.0,
            n_evals=int(len(representations)),
            details={
                "split": split,
                "top_k": self.top_k,
                "top_k_by_true_quality": float(np.mean(top_oracle)) if len(top_oracle) else None,
                "population_mean": float(np.mean(q)) if len(q) else None,
                "best": float(np.max(q)) if len(q) else None,
                "n_invalid": int((~valid).sum()),
            },
        )

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "higher_is_better": True, "top_k": self.top_k, "ranking": "population order (system ranking)",
                "draws": SPLIT_DRAWS, "synthetic": True}


# ----------------------------------------------------------------------------- task 1
class RobustDesignValidator(NumericTaskValidator):
    """Expected performance under manufacturing tolerance (std 0.08), with a hard failure boundary."""

    name = "robust_design_truth"
    dim = 8
    center = np.array([0.70, 0.62, 0.45, 0.55, 0.38, 0.60, 0.50, 0.42])
    width = 0.35
    tolerance = 0.08

    def _performance(self, X):
        bump = np.exp(-np.sum((X - self.center) ** 2, axis=-1) / (2 * self.width ** 2))
        return np.where(X[..., 0] + X[..., 1] <= 1.0, bump, 0.0)

    def quality(self, X, split):
        rng = np.random.default_rng(SPLIT_SEEDS[split] + 1)
        noise = rng.normal(0.0, self.tolerance, size=(SPLIT_DRAWS[split], 1, self.dim))
        return self._performance(np.clip(X[None, :, :] + noise, 0.0, 1.0)).mean(axis=0)


# ----------------------------------------------------------------------------- task 2
class ConstrainedYieldValidator(NumericTaskValidator):
    """Expected yield over market scenarios; designs over the cost budget are worth zero."""

    name = "constrained_yield_truth"
    dim = 6
    a_nominal = np.array([1.0, 0.8, 1.2, 0.6, 0.9, 1.1])
    b = np.array([1.0, 1.5, 2.0, 0.5, 1.2, 1.8])
    budget = 0.15
    scenario_sigma = 0.3

    def quality(self, X, split):
        rng = np.random.default_rng(SPLIT_SEEDS[split] + 2)
        a = self.a_nominal * np.exp(self.scenario_sigma * rng.normal(size=(SPLIT_DRAWS[split], self.dim)))
        yields = (np.sqrt(X) @ a.T) / self.a_nominal.sum()          # (n, scenarios)
        cost = (X ** 2) @ self.b / self.b.sum()
        return np.where(cost <= self.budget, yields.mean(axis=1), 0.0)


# ----------------------------------------------------------------------------- task 3
class SpectralSignalValidator(NumericTaskValidator):
    """Spectral match to a (split-specific measurement of the) target times smoothness, under actuation noise."""

    name = "spectral_signal_truth"
    dim = 12
    actuation_noise = 0.02
    k = np.arange(12)
    target_signal = 0.5 + 0.25 * np.sin(2 * np.pi * k / 12) + 0.12 * np.cos(2 * np.pi * 2 * k / 12 + 0.4)
    target_spectrum = np.abs(np.fft.rfft(target_signal))[:5] / 12
    se_scale = 0.01
    roughness_scale = 2.0

    def _quality_once(self, S, target):
        spectrum = np.abs(np.fft.rfft(S, axis=-1))[..., :5] / 12
        se = np.sum((spectrum - target) ** 2, axis=-1)
        rough = np.sum((S[..., 2:] - 2 * S[..., 1:-1] + S[..., :-2]) ** 2, axis=-1)
        return np.exp(-se / self.se_scale) * np.exp(-rough / self.roughness_scale)

    def quality(self, X, split):
        rng = np.random.default_rng(SPLIT_SEEDS[split] + 3)
        target = self.target_spectrum * (1.0 + 0.05 * rng.normal(size=5))
        noise = rng.normal(0.0, self.actuation_noise, size=(SPLIT_DRAWS[split], 1, self.dim))
        return self._quality_once(np.clip(X[None, :, :] + noise, 0.0, 1.0), target).mean(axis=0)


# ----------------------------------------------------------------------------- v2 tasks
class _BumpValidator(NumericTaskValidator):
    """Gaussian-bump quality under small actuation noise (std 0.02); written independently of the scorers."""

    dim = 8
    center = None
    width = None
    actuation_noise = 0.02
    seed_offset = 0

    def quality(self, X, split):
        rng = np.random.default_rng(SPLIT_SEEDS[split] + self.seed_offset)
        noise = rng.normal(0.0, self.actuation_noise, size=(SPLIT_DRAWS[split], 1, self.dim))
        S = np.clip(X[None, :, :] + noise, 0.0, 1.0)
        return np.exp(-np.sum((S - self.center) ** 2, axis=-1) / (2 * self.width ** 2)).mean(axis=0)


class StagnantSearchValidator(_BumpValidator):
    name = "stagnant_search_truth"
    center = np.array([0.25, 0.72, 0.40, 0.63, 0.31, 0.55, 0.78, 0.46])
    width = 0.22
    seed_offset = 11


class OverflowScorerValidator(_BumpValidator):
    """True quality of the overflow task: the bump only (the scorer's overflow branch is a bug)."""

    name = "overflow_scorer_truth"
    center = np.array([0.45, 0.60, 0.35, 0.55, 0.50, 0.40, 0.65, 0.52])
    width = 0.25
    seed_offset = 12


class NoisySearchValidator(_BumpValidator):
    name = "noisy_search_truth"
    center = np.array([0.62, 0.38, 0.70, 0.45, 0.58, 0.30, 0.52, 0.66])
    width = 0.15
    seed_offset = 13


class UnderflowCostValidator(_BumpValidator):
    """Held-out v2b task: true quality is the bump only (the cost scorer's underflow branch is a bug)."""

    name = "underflow_cost_truth"
    center = np.array([0.55, 0.35, 0.60, 0.42, 0.68, 0.50, 0.30, 0.58])
    width = 0.22
    seed_offset = 14


class FrozenMutationValidator(NumericTaskValidator):
    """Held-out v3 task: anisotropic rotated bump under small actuation noise (std 0.02)."""

    name = "frozen_mutation_truth"
    dim = 8
    center = np.array([0.38, 0.66, 0.52, 0.29, 0.61, 0.45, 0.70, 0.34])
    _q, _ = np.linalg.qr(np.random.default_rng(42).normal(size=(8, 8)))
    precision = _q @ np.diag(1.0 / np.array([0.06, 0.08, 0.10, 0.14, 0.2, 0.3, 0.4, 0.5]) ** 2) @ _q.T

    def quality(self, X, split):
        rng = np.random.default_rng(SPLIT_SEEDS[split] + 15)
        S = np.clip(X[None, :, :] + rng.normal(0.0, 0.02, size=(SPLIT_DRAWS[split], 1, self.dim)), 0.0, 1.0) - self.center
        return np.exp(-0.5 * np.einsum("dni,ij,dnj->dn", S, self.precision, S)).mean(axis=0)


class OffsetScorerValidator(_BumpValidator):
    """Held-out v3 task: true quality is the bump only (the scorer's offset branch is a bug)."""

    name = "offset_scorer_truth"
    center = np.array([0.52, 0.41, 0.63, 0.40, 0.35, 0.58, 0.47, 0.55])
    width = 0.22
    seed_offset = 16


VALIDATOR_CLASSES = {cls.name: cls for cls in (RobustDesignValidator, ConstrainedYieldValidator, SpectralSignalValidator,
                                               StagnantSearchValidator, OverflowScorerValidator, NoisySearchValidator,
                                               UnderflowCostValidator, FrozenMutationValidator, OffsetScorerValidator)}


def register_numeric_validators() -> None:
    from scileo_agent.meta_controller.validators import list_validators

    existing = set(list_validators())
    for name, cls in VALIDATOR_CLASSES.items():
        if name not in existing:
            register_validator(name, cls)


def get_numeric_validator(name: str) -> Optional[NumericTaskValidator]:
    cls = VALIDATOR_CLASSES.get(name)
    return cls() if cls else None
