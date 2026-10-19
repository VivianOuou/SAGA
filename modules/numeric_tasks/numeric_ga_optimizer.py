"""
Real-valued genetic algorithm for the synthetic numeric tasks (no LLM calls).

Fitness is a weighted sum of per-objective ranks within the current population (None / failed
evaluations rank worst), with filter objectives as a hard penalty. The evaluation quota per call is
fixed by `pop_size` and `generations`; the tunable parameters below do not change it, so the
Meta-Controller can compare settings at equal cost.
"""

from typing import Any, Dict, List, Optional

import numpy as np

from scileo_agent.core.data_models import Candidate, Objective, Population
from scileo_agent.core.modules import OptimizerModule
from scileo_agent.core.registry.module_registry import register_module


TUNABLE_PARAMS = {
    "mutation_sigma": {"type": "float", "min": 0.005, "max": 0.5, "description": "std of the Gaussian mutation applied to a gene"},
    "mutation_prob": {"type": "float", "min": 0.0, "max": 1.0, "description": "per-gene mutation probability"},
    "crossover_rate": {"type": "float", "min": 0.0, "max": 1.0, "description": "probability of uniform crossover between two parents"},
    "elite_fraction": {"type": "float", "min": 0.0, "max": 0.5, "description": "fraction of the best candidates copied unchanged to the next generation"},
    "tournament_size": {"type": "int", "min": 2, "max": 8, "description": "tournament size (selection pressure)"},
}

DEFAULTS = {"mutation_sigma": 0.08, "mutation_prob": 0.3, "crossover_rate": 0.7, "elite_fraction": 0.1, "tournament_size": 3}


@register_module("numeric_ga_optimizer", "0.1.0")
class NumericGAOptimizer(OptimizerModule):
    def __init__(self, module_id: str, config: Optional[Dict[str, Any]] = None, llm_config=None):
        super().__init__(module_id, config, llm_config)
        cfg = self.config
        self.dim = int(cfg["dim"])
        self.pop_size = int(cfg.get("pop_size", 32))
        self.generations = int(cfg.get("generations", 10))
        self.seed = int(cfg.get("seed", 0))
        self.rng = np.random.default_rng(self.seed)
        for name, default in DEFAULTS.items():
            setattr(self, name, cfg.get(name, default))
        self.set_tunable_params({name: getattr(self, name) for name in DEFAULTS})
        self.num_evaluations = 0

    # --------------------------------------------------------------- Meta-Controller hooks
    def tunable_params(self) -> Dict[str, Dict[str, Any]]:
        return {name: dict(spec, current=getattr(self, name)) for name, spec in TUNABLE_PARAMS.items()}

    def set_tunable_params(self, params: Dict[str, Any]) -> None:
        for name, value in params.items():
            spec = TUNABLE_PARAMS.get(name)
            if spec is None:
                raise ValueError(f"'{name}' is not a tunable parameter of {self.__class__.__name__}")
            value = int(round(value)) if spec["type"] == "int" else float(value)
            if not spec["min"] <= value <= spec["max"]:
                raise ValueError(f"'{name}'={value} outside [{spec['min']}, {spec['max']}]")
            setattr(self, name, value)

    def estimate_evaluations(self, **overrides) -> int:
        pop = int(overrides.get("pop_size", self.pop_size))
        gens = int(overrides.get("generations", self.generations))
        return pop * (gens + 1)

    # --------------------------------------------------------------- OptimizerModule API
    def _random_vector(self) -> List[float]:
        return [round(float(v), 6) for v in self.rng.random(self.dim)]

    async def create_random_candidates(self, num_candidates: int, **additional_kwargs) -> List[Candidate]:
        return [Candidate(representation=self._random_vector()) for _ in range(num_candidates)]

    async def _evaluate(self, candidates: List[Candidate], objectives: List[Objective]) -> None:
        names = [o.name for o in objectives]
        self.num_evaluations += sum(1 for c in candidates if any(n not in c.scores for n in names))
        population = Population(candidates=candidates)
        for objective in objectives:
            await objective.score(population)

    def _fitness(self, candidates: List[Candidate], objectives: List[Objective]) -> np.ndarray:
        n = len(candidates)
        fitness = np.zeros(n)
        for objective in objectives:
            if objective.type == "population-wise":
                continue
            values = [c.scores.get(objective.name) for c in candidates]
            if objective.type == "filter":
                fitness -= 10.0 * np.array([not bool(v) for v in values], dtype=float)
                continue
            arr = np.array([np.nan if v is None else float(v) for v in values], dtype=float)
            arr[~np.isfinite(arr)] = np.nan
            valid = ~np.isnan(arr)
            ranks = np.zeros(n)
            if valid.sum() > 1:
                sign = 1.0 if objective.optimization_direction == "maximize" else -1.0
                order = np.argsort(np.argsort(sign * arr[valid], kind="stable"), kind="stable")
                ranks[valid] = order / (valid.sum() - 1)
            elif valid.sum() == 1:
                ranks[valid] = 1.0
            weight = objective.weight if objective.weight is not None else 1.0
            fitness += weight * ranks
        return fitness

    def _tournament(self, fitness: np.ndarray) -> int:
        idx = self.rng.choice(len(fitness), size=min(int(self.tournament_size), len(fitness)), replace=False)
        return int(idx[np.argmax(fitness[idx])])

    async def optimize(self, current_population: Optional[Population], objectives: List[Objective], **additional_kwargs) -> Population:
        candidates = list(current_population.candidates) if current_population else []
        while len(candidates) < self.pop_size:
            candidates.append(Candidate(representation=self._random_vector()))
        await self._evaluate(candidates, objectives)
        order = np.argsort(-self._fitness(candidates, objectives), kind="stable")
        candidates = [candidates[i] for i in order[: self.pop_size]]

        for _ in range(self.generations):
            fitness = self._fitness(candidates, objectives)
            n_elite = int(round(self.elite_fraction * self.pop_size))
            order = np.argsort(-fitness, kind="stable")
            elites = [candidates[i] for i in order[:n_elite]]
            children = []
            while len(children) < self.pop_size - n_elite:
                x1 = np.asarray(candidates[self._tournament(fitness)].representation, dtype=float)
                x2 = np.asarray(candidates[self._tournament(fitness)].representation, dtype=float)
                if self.rng.random() < self.crossover_rate:
                    child = np.where(self.rng.random(self.dim) < 0.5, x1, x2)
                else:
                    child = x1.copy()
                mutate = self.rng.random(self.dim) < self.mutation_prob
                child = np.clip(child + mutate * self.rng.normal(0.0, self.mutation_sigma, self.dim), 0.0, 1.0)
                children.append(Candidate(representation=[round(float(v), 6) for v in child]))
            await self._evaluate(children, objectives)
            candidates = elites + children

        order = np.argsort(-self._fitness(candidates, objectives), kind="stable")
        return Population(candidates=[candidates[i] for i in order])
