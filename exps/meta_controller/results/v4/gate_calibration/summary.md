# Gate calibration (offline, no LLM)

OFFLINE, no LLM: mock planner/analyzer, real GA/controller/validators, in-process scorers

| condition | task | probe | true effect (mean of 5 seeds) | class | old gate accepted | new gate accepted | new mean stages |
|---|---|---|---|---|---|---|---|
| initial | stagnant_search | fix:mutation_sigma=0.08 | +0.796 | beneficial | 5/5 | 5/5 | 1.0 |
| initial | stagnant_search | random_candidate_ratio=0.5 | +0.114 | beneficial | 2/5 | 2/5 | 1.6 |
| initial | stagnant_search | add parameter_spread max w5 | -0.130 | harmful | 0/5 | 0/5 | 1.0 |
| initial | noisy_search | fix:mutation_sigma=0.05 | +0.784 | beneficial | 5/5 | 5/5 | 1.0 |
| initial | noisy_search | tournament_size=2 | -0.002 | neutral | 0/5 | 0/5 | 1.2 |
| initial | noisy_search | add distance_from_center min w5 | -0.005 | neutral | 0/5 | 0/5 | 1.6 |
| initial | frozen_mutation | fix:mutation_prob=0.3 | +0.624 | beneficial | 5/5 | 5/5 | 1.0 |
| initial | frozen_mutation | mutation_sigma=0.3 | +0.000 | neutral | 0/5 | 0/5 | 1.0 |
| initial | frozen_mutation | add parameter_spread max w5 | -0.019 | neutral | 0/5 | 0/5 | 1.0 |
| initial | overflow_scorer | fix:sanitize[0,1] | +0.965 | beneficial | 5/5 | 5/5 | 1.0 |
| initial | overflow_scorer | sanitize[0,0.3] | +0.289 | beneficial | 5/5 | 5/5 | 1.0 |
| initial | overflow_scorer | mutation_sigma=0.3 | -0.001 | neutral | 0/5 | 0/5 | 1.4 |
| initial | underflow_cost | fix:sanitize[0,1] | +0.958 | beneficial | 5/5 | 5/5 | 1.0 |
| initial | underflow_cost | sanitize[0.5,1] | +0.480 | beneficial | 5/5 | 5/5 | 1.0 |
| initial | underflow_cost | add parameter_mean max w5 | -0.001 | neutral | 0/5 | 0/5 | 1.0 |
| initial | offset_scorer | fix:sanitize[0,1] | +0.953 | beneficial | 5/5 | 5/5 | 1.0 |
| initial | offset_scorer | sanitize[0,0.3] | +0.292 | beneficial | 5/5 | 5/5 | 1.0 |
| initial | offset_scorer | add parameter_spread min w1 | -0.000 | neutral | 0/5 | 0/5 | 2.8 |
| planner_observed | stagnant_search | fix:mutation_sigma=0.08 | +0.750 | beneficial | 4/5 | 5/5 | 1.2 |
| planner_observed | stagnant_search | random_candidate_ratio=0.5 | +0.030 | neutral | 2/5 | 3/5 | 1.4 |
| planner_observed | stagnant_search | add parameter_spread max w5 | +0.000 | not_applicable | 0/5 | 0/5 | 0.0 |
| planner_observed | noisy_search | fix:mutation_sigma=0.05 | -0.000 | neutral | 0/5 | 3/5 | 1.6 |
| planner_observed | noisy_search | tournament_size=2 | +0.000 | neutral | 0/5 | 0/5 | 1.6 |
| planner_observed | noisy_search | add distance_from_center min w5 | +0.000 | not_applicable | 0/5 | 0/5 | 0.0 |
| planner_observed | frozen_mutation | fix:mutation_prob=0.3 | +0.291 | beneficial | 5/5 | 5/5 | 1.0 |
| planner_observed | frozen_mutation | mutation_sigma=0.3 | +0.000 | neutral | 0/5 | 0/5 | 1.0 |
| planner_observed | frozen_mutation | add parameter_spread max w5 | +0.000 | not_applicable | 0/5 | 0/5 | 0.0 |
| planner_observed | overflow_scorer | fix:sanitize[0,1] | +0.195 | beneficial | 0/5 | 2/5 | 2.6 |
| planner_observed | overflow_scorer | sanitize[0,0.3] | +0.076 | beneficial | 0/5 | 2/5 | 2.6 |
| planner_observed | overflow_scorer | mutation_sigma=0.3 | +0.000 | neutral | 0/5 | 0/5 | 2.6 |
| planner_observed | underflow_cost | fix:sanitize[0,1] | +0.955 | beneficial | 5/5 | 5/5 | 1.0 |
| planner_observed | underflow_cost | sanitize[0.5,1] | +0.481 | beneficial | 5/5 | 5/5 | 1.0 |
| planner_observed | underflow_cost | add parameter_mean max w5 | -0.000 | neutral | 1/5 | 1/5 | 1.4 |
| planner_observed | offset_scorer | fix:sanitize[0,1] | +0.002 | neutral | 0/5 | 0/5 | 3.0 |
| planner_observed | offset_scorer | sanitize[0,0.3] | +0.002 | neutral | 0/5 | 0/5 | 3.0 |
| planner_observed | offset_scorer | add parameter_spread min w1 | +0.000 | not_applicable | 0/5 | 0/5 | 0.0 |

| condition | gate | beneficial accepted | harmful accepted (false accept) | neutral accepted | mean evals per decision |
|---|---|---|---|---|---|
| initial | old | 47/50 | 0/5 | 0/35 | 1308.0 |
| initial | new | 47/50 | 0/5 | 0/35 | 1566.0 |
| planner_observed | old | 19/30 | 0/0 | 3/40 | 1295.0 |
| planner_observed | new | 24/30 | 0/0 | 7/40 | 2308.0 |
| all | old | 66/80 | 0/5 | 3/75 | 1302.0 |
| all | new | 71/80 | 0/5 | 7/75 | 1891.0 |
