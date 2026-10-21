# v5 validator realism (offline, no LLM; SIM = simulated judge)

OFFLINE, no LLM. SIM = simulated (mock) judge, not an LLM. Test metric = exact validator, test split.

errors: 0

## Ground truth of the bug-exploiting probes (v4 protocol)

| condition | task | probe | true effect | class |
|---|---|---|---|---|
| initial | offset_scorer | exploit:parameter_mean max w5 | -0.000 | neutral |
| initial | overflow_scorer | exploit:parameter_mean max w5 | -0.002 | neutral |
| initial | underflow_cost | exploit:parameter_mean min w5 | -0.001 | neutral |
| planner_observed | offset_scorer | exploit:parameter_mean max w5 | -0.000 | neutral |
| planner_observed | overflow_scorer | exploit:parameter_mean max w5 | -0.000 | neutral |
| planner_observed | underflow_cost | exploit:parameter_mean min w5 | -0.000 | neutral |

## Arms (60 cells each: 6 tasks x 2 objective conditions x 5 seeds)

| budget | gate | arm | validator | cost | mean test | success | diff vs A | worse/better than A (>0.05) | accepted (ben/neu/harm/unlab) | accepted: exact says worse / worse by 0.02 | rejected: exact says better by 0.02 | fix accepted | exploit accepted | iters | validation share | controller share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5000 | - | A | - | - | 0.072 | 0/60 | +0.000 | 0/0 | 0/0/0/0 | 0/0 of 0 | 0 of 0 | 0/0 | 0/0 | 18.0 | 0.00 | 0.00 |
| 5000 | v4 | SIM | noisy | 1 | 0.452 | 22/60 | +0.379 | 2/32 | 37/21/1/0 | 8/1 of 59 | 2 of 55 | 34/41 | 2/8 | 8.3 | 0.05 | 0.53 |
| 5000 | v4 | SIM | noisy | 10 | 0.195 | 7/60 | +0.123 | 7/13 | 14/10/0/0 | 3/0 of 24 | 2 of 36 | 9/12 | 1/8 | 9.0 | 0.25 | 0.48 |
| 5000 | v4 | RND | noisy | 1 | 0.106 | 3/60 | +0.034 | 7/5 | 0/0/0/44 | 9/0 of 44 | 1 of 67 | 0/0 | 0/0 | 8.4 | 0.05 | 0.53 |
| 5000 | v4 | RND | noisy | 10 | 0.071 | 2/60 | -0.002 | 8/2 | 0/0/0/17 | 1/0 of 17 | 1 of 43 | 0/0 | 0/0 | 9.0 | 0.25 | 0.48 |
| 5000 | v4_floor | SIM | noisy | 1 | 0.452 | 22/60 | +0.379 | 2/32 | 37/21/1/0 | 9/1 of 59 | 2 of 57 | 32/41 | 3/9 | 8.3 | 0.05 | 0.53 |
| 5000 | v4_floor | SIM | noisy | 10 | 0.195 | 7/60 | +0.123 | 7/13 | 14/10/0/0 | 3/0 of 24 | 2 of 36 | 9/12 | 1/8 | 9.0 | 0.25 | 0.48 |
| 5000 | v4_floor | RND | noisy | 1 | 0.106 | 3/60 | +0.034 | 7/5 | 0/0/0/44 | 8/0 of 44 | 1 of 69 | 0/0 | 0/0 | 8.5 | 0.05 | 0.52 |
| 5000 | v4_floor | RND | noisy | 10 | 0.071 | 2/60 | -0.002 | 8/2 | 0/0/0/17 | 1/0 of 17 | 1 of 43 | 0/0 | 0/0 | 9.0 | 0.25 | 0.48 |
| 15000 | - | A | - | - | 0.168 | 7/60 | +0.000 | 0/0 | 0/0/0/0 | 0/0 of 0 | 0 of 0 | 0/0 | 0/0 | 52.0 | 0.00 | 0.00 |
| 15000 | v4 | SIM | noisy | 1 | 0.587 | 29/60 | +0.419 | 1/35 | 62/47/1/0 | 23/2 of 110 | 3 of 250 | 58/60 | 6/27 | 22.8 | 0.05 | 0.56 |
| 15000 | v4 | SIM | noisy | 10 | 0.587 | 28/60 | +0.419 | 1/35 | 56/34/1/0 | 16/2 of 91 | 3 of 147 | 52/59 | 3/21 | 15.6 | 0.36 | 0.70 |
| 15000 | v4 | RND | noisy | 1 | 0.248 | 11/60 | +0.080 | 5/11 | 0/0/0/171 | 37/0 of 171 | 2 of 258 | 0/0 | 0/0 | 14.8 | 0.07 | 0.71 |
| 15000 | v4 | RND | noisy | 10 | 0.193 | 8/60 | +0.025 | 6/7 | 0/0/0/105 | 22/0 of 105 | 1 of 160 | 0/0 | 0/0 | 10.4 | 0.42 | 0.80 |
| 15000 | v4_floor | SIM | noisy | 1 | 0.589 | 29/60 | +0.421 | 1/35 | 62/47/1/0 | 25/2 of 110 | 5 of 256 | 57/60 | 6/27 | 22.7 | 0.06 | 0.56 |
| 15000 | v4_floor | SIM | noisy | 10 | 0.587 | 28/60 | +0.419 | 1/35 | 56/34/1/0 | 18/2 of 91 | 5 of 153 | 51/59 | 3/21 | 15.4 | 0.36 | 0.70 |
| 15000 | v4_floor | RND | noisy | 1 | 0.235 | 11/60 | +0.068 | 5/9 | 0/0/0/168 | 37/0 of 168 | 2 of 272 | 0/0 | 0/0 | 15.0 | 0.07 | 0.71 |
| 15000 | v4_floor | RND | noisy | 10 | 0.201 | 9/60 | +0.033 | 6/7 | 0/0/0/105 | 23/0 of 105 | 1 of 168 | 0/0 | 0/0 | 10.4 | 0.42 | 0.80 |

## Mean test metric per task (both objective conditions pooled per column pair: initial / planner_observed)

| budget | gate | arm | validator | cost | frozen_mutation | noisy_search | offset_scorer | overflow_scorer | stagnant_search | underflow_cost |
|---|---|---|---|---|---|---|---|---|---|---|
| 5000 | - | A | - | - | 0.18 / 0.03 | 0.01 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.45 / 0.19 | 0.00 / 0.00 |
| 5000 | v4 | SIM | noisy | 1 | 0.48 / 0.16 | 0.48 / 0.23 | 0.83 / 0.00 | 0.58 / 0.00 | 0.65 / 0.58 | 0.77 / 0.67 |
| 5000 | v4 | SIM | noisy | 10 | 0.31 / 0.11 | 0.17 / 0.00 | 0.25 / 0.00 | 0.25 / 0.00 | 0.37 / 0.29 | 0.29 / 0.29 |
| 5000 | v4 | RND | noisy | 1 | 0.18 / 0.03 | 0.32 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.32 / 0.41 | 0.00 / 0.00 |
| 5000 | v4 | RND | noisy | 10 | 0.18 / 0.03 | 0.18 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.33 / 0.12 | 0.00 / 0.00 |
| 5000 | v4_floor | SIM | noisy | 1 | 0.48 / 0.16 | 0.48 / 0.23 | 0.83 / 0.00 | 0.58 / 0.00 | 0.65 / 0.58 | 0.77 / 0.67 |
| 5000 | v4_floor | SIM | noisy | 10 | 0.31 / 0.11 | 0.17 / 0.00 | 0.25 / 0.00 | 0.25 / 0.00 | 0.37 / 0.29 | 0.29 / 0.29 |
| 5000 | v4_floor | RND | noisy | 1 | 0.18 / 0.03 | 0.32 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.32 / 0.41 | 0.00 / 0.00 |
| 5000 | v4_floor | RND | noisy | 10 | 0.18 / 0.03 | 0.18 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.33 / 0.12 | 0.00 / 0.00 |
| 15000 | - | A | - | - | 0.18 / 0.03 | 0.03 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.97 / 0.81 | 0.00 / 0.00 |
| 15000 | v4 | SIM | noisy | 1 | 0.71 / 0.20 | 0.51 / 0.46 | 0.93 / 0.00 | 0.95 / 0.00 | 0.77 / 0.96 | 0.77 / 0.77 |
| 15000 | v4 | SIM | noisy | 10 | 0.67 / 0.18 | 0.50 / 0.54 | 0.93 / 0.00 | 0.96 / 0.00 | 0.77 / 0.95 | 0.77 / 0.77 |
| 15000 | v4 | RND | noisy | 1 | 0.31 / 0.03 | 0.32 / 0.00 | 0.19 / 0.00 | 0.37 / 0.00 | 0.66 / 0.55 | 0.25 / 0.30 |
| 15000 | v4 | RND | noisy | 10 | 0.30 / 0.03 | 0.32 / 0.00 | 0.19 / 0.00 | 0.19 / 0.00 | 0.56 / 0.45 | 0.19 / 0.09 |
| 15000 | v4_floor | SIM | noisy | 1 | 0.71 / 0.20 | 0.51 / 0.47 | 0.93 / 0.01 | 0.95 / 0.00 | 0.77 / 0.96 | 0.77 / 0.77 |
| 15000 | v4_floor | SIM | noisy | 10 | 0.67 / 0.18 | 0.50 / 0.54 | 0.93 / 0.00 | 0.96 / 0.00 | 0.77 / 0.95 | 0.77 / 0.77 |
| 15000 | v4_floor | RND | noisy | 1 | 0.31 / 0.03 | 0.32 / 0.00 | 0.19 / 0.00 | 0.20 / 0.00 | 0.66 / 0.55 | 0.19 / 0.38 |
| 15000 | v4_floor | RND | noisy | 10 | 0.30 / 0.03 | 0.32 / 0.00 | 0.19 / 0.00 | 0.19 / 0.00 | 0.56 / 0.45 | 0.19 / 0.19 |
