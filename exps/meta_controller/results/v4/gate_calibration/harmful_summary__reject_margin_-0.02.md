# Supplementary false-accept check (healthy optimizer settings, offline, no LLM)

| task | probe | true effect (mean of 5 seeds) | class | old gate accepted | new gate accepted |
|---|---|---|---|---|---|
| stagnant_search | mutation_prob=0.0 | -0.042 | neutral | 0/5 | 0/5 |
| stagnant_search | mutation_sigma=0.5 | -0.165 | harmful | 0/5 | 0/5 |
| stagnant_search | add parameter_spread max w5 | -0.959 | harmful | 0/5 | 0/5 |
| noisy_search | mutation_prob=0.0 | -0.081 | harmful | 2/5 | 2/5 |
| noisy_search | mutation_sigma=0.5 | -0.255 | harmful | 0/5 | 0/5 |
| noisy_search | add parameter_spread max w5 | -0.909 | harmful | 0/5 | 0/5 |
| frozen_mutation | mutation_prob=0.0 | -0.321 | harmful | 0/5 | 0/5 |
| frozen_mutation | mutation_sigma=0.5 | -0.378 | harmful | 0/5 | 0/5 |
| frozen_mutation | add parameter_spread max w5 | -0.830 | harmful | 0/5 | 0/5 |

Harmful changes accepted (false accepts): old 2/40, new 2/40
