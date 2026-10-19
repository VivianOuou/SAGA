"""
Fix success thresholds for the SYNTHETIC numeric tasks BEFORE any A/B run.

For each task an oracle GA optimizes the validator's *calibration* split directly (never the test
split) to estimate the attainable quality q*. The success threshold is 0.9 * q*. Also reports the
metric of the random initial population for reference.

Usage (from the repository root):
    python exps/meta_controller/calibrate_tasks.py
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from modules.numeric_tasks.tasks import TASKS, THRESHOLDS_FILE, initial_population_vectors  # noqa: E402
from modules.numeric_tasks.validators import get_numeric_validator  # noqa: E402


def oracle_ga(validator, dim, seed, pop=64, gens=250, sigma=0.05):
    rng = np.random.default_rng(seed)
    X = rng.random((pop, dim))
    for _ in range(gens):
        q = validator.quality(X, "calibration")
        order = np.argsort(-q)
        elite = X[order[: pop // 4]]
        parents = elite[rng.integers(0, len(elite), size=(pop - len(elite), 2))]
        mask = rng.random((pop - len(elite), dim)) < 0.5
        children = np.where(mask, parents[:, 0], parents[:, 1])
        children = np.clip(children + rng.normal(0, sigma, children.shape) * (rng.random(children.shape) < 0.3), 0, 1)
        X = np.vstack([elite, children])
    order = np.argsort(-validator.quality(X, "calibration"))  # oracle ranks by the truth itself
    reps = [list(map(float, X[i])) for i in order]
    return validator.evaluate(reps, split="calibration").metric


def main():
    out = {}
    for task_id, task in TASKS.items():
        validator = get_numeric_validator(task.validator)
        q_star = max(oracle_ga(validator, task.dim, seed) for seed in range(3))
        random_metric = validator.evaluate(initial_population_vectors(task.dim, 32, 0), split="calibration").metric
        out[task_id] = {
            "oracle_q_star_calibration_split": round(q_star, 4),
            "random_initial_population_metric": round(random_metric, 4),
            "success_threshold": round(0.9 * q_star, 3),
            "rule": "success iff final test-split metric (mean true quality of the 5 top-ranked candidates of the final population) >= 0.9 * q_star",
        }
        print(task_id, out[task_id])
    THRESHOLDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(THRESHOLDS_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {THRESHOLDS_FILE}")


if __name__ == "__main__":
    main()
