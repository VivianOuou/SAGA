# Meta-Controller A/B summary (offline_mock)

MOCK planner/analyzer/judge: pipeline check only, not evidence

| task | seed | arm | status | term. | iters | success | test metric | thr | LLM calls | tokens | cost $ | evals | first target (best) | controller outcomes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| noisy_search | 0 | A | completed | budget_exhausted | 18 | False | 0.009 | 0.839 | 36 | 9000 | 0.0000 | 5252 |  |  |
| noisy_search | 0 | B | completed | budget_exhausted | 13 | False | 0.792 | 0.839 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| noisy_search | 0 | C | completed | budget_exhausted | 9 | True | 0.894 | 0.839 | 18 | 4500 | 0.0000 | 5218 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 1, "rejected": 1, "skipped": 6} |
| noisy_search | 1 | A | completed | budget_exhausted | 18 | False | 0.009 | 0.839 | 36 | 9000 | 0.0000 | 5252 |  |  |
| noisy_search | 1 | B | completed | budget_exhausted | 13 | True | 0.856 | 0.839 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| noisy_search | 1 | C | completed | budget_exhausted | 9 | False | 0.009 | 0.839 | 20 | 4900 | 0.0000 | 5282 | planning (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| noisy_search | 2 | A | completed | budget_exhausted | 18 | False | 0.006 | 0.839 | 36 | 9000 | 0.0000 | 5252 |  |  |
| noisy_search | 2 | B | completed | budget_exhausted | 13 | False | 0.830 | 0.839 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| noisy_search | 2 | C | completed | budget_exhausted | 9 | False | 0.006 | 0.839 | 20 | 4900 | 0.0000 | 5218 | objective (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| overflow_scorer | 0 | A | completed | budget_exhausted | 18 | False | 0.001 | 0.878 | 36 | 9000 | 0.0000 | 5252 |  |  |
| overflow_scorer | 0 | B | completed | budget_exhausted | 13 | True | 0.971 | 0.878 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| overflow_scorer | 0 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 18 | 4500 | 0.0000 | 5218 | optimization_workflow (implementation) | {"rejected": 2, "no_change": 1, "skipped": 6} |
| overflow_scorer | 1 | A | completed | budget_exhausted | 18 | False | 0.000 | 0.878 | 36 | 9000 | 0.0000 | 5252 |  |  |
| overflow_scorer | 1 | B | completed | budget_exhausted | 13 | True | 0.973 | 0.878 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| overflow_scorer | 1 | C | completed | budget_exhausted | 8 | False | 0.000 | 0.878 | 18 | 4400 | 0.0000 | 5024 | planning (implementation) | {"rejected": 1, "accepted": 1, "skipped": 6} |
| overflow_scorer | 2 | A | completed | budget_exhausted | 18 | False | 0.003 | 0.878 | 36 | 9000 | 0.0000 | 5252 |  |  |
| overflow_scorer | 2 | B | completed | budget_exhausted | 13 | True | 0.964 | 0.878 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| overflow_scorer | 2 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 20 | 4900 | 0.0000 | 5218 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| stagnant_search | 0 | A | completed | budget_exhausted | 18 | False | 0.621 | 0.874 | 36 | 9000 | 0.0000 | 5252 |  |  |
| stagnant_search | 0 | B | completed | budget_exhausted | 13 | True | 0.967 | 0.874 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| stagnant_search | 0 | C | completed | budget_exhausted | 9 | False | 0.871 | 0.874 | 18 | 4500 | 0.0000 | 5218 | optimization_workflow (optimization_workflow) | {"accepted": 2, "no_change": 1, "skipped": 6} |
| stagnant_search | 1 | A | completed | budget_exhausted | 18 | False | 0.251 | 0.874 | 36 | 9000 | 0.0000 | 5252 |  |  |
| stagnant_search | 1 | B | completed | budget_exhausted | 13 | True | 0.967 | 0.874 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| stagnant_search | 1 | C | completed | budget_exhausted | 9 | False | 0.078 | 0.874 | 20 | 4900 | 0.0000 | 5282 | planning (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| stagnant_search | 2 | A | completed | budget_exhausted | 18 | False | 0.262 | 0.874 | 36 | 9000 | 0.0000 | 5252 |  |  |
| stagnant_search | 2 | B | completed | budget_exhausted | 13 | True | 0.967 | 0.874 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| stagnant_search | 2 | C | completed | budget_exhausted | 9 | False | 0.073 | 0.874 | 20 | 4900 | 0.0000 | 5218 | objective (optimization_workflow) | {"rejected": 2, "skipped": 7} |

## Per-arm totals

| arm | runs | success | LLM calls | tokens (observed) | cost $ | oracle evals |
|---|---|---|---|---|---|---|
| A | 9 | 0 | 324 | 81000 | 0.000 | 47268 |
| B | 9 | 7 | 288 | 61200 | 0.000 | 45810 |
| C | 9 | 1 | 172 | 42400 | 0.000 | 46896 |

## Paired test-metric differences

- B-A: mean 0.792; 9 better / 0 worse of 9 pairs
- C-A: mean 0.085; 2 better / 7 worse of 9 pairs
- B-C: mean 0.706; 8 better / 1 worse of 9 pairs

## Controller target statistics

```
{
 "B": {
  "proposals": 54,
  "target:optimization_workflow": 6,
  "proposals_on_best_target": 9,
  "accepted": 9,
  "accepted_on_best_target": 9,
  "outcome:accepted": 9,
  "target:no_change": 45,
  "outcome:no_change": 45,
  "outcome:skipped": 63,
  "runs_first_proposal_on_best_target": 9,
  "runs_with_proposals": 9,
  "target:implementation": 3
 },
 "C": {
  "proposals": 21,
  "target:optimization_workflow": 6,
  "proposals_on_best_target": 4,
  "accepted": 4,
  "accepted_on_best_target": 3,
  "outcome:accepted": 4,
  "target:no_change": 3,
  "outcome:no_change": 3,
  "outcome:rejected": 14,
  "outcome:skipped": 59,
  "runs_first_proposal_on_best_target": 2,
  "runs_with_proposals": 9,
  "target:planning": 6,
  "target:objective": 6
 }
}
```
