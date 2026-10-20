# Meta-Controller A/B summary (real_llm)

REAL LLM calls on SYNTHETIC numeric tasks; small pilot, no significance testing

| task | seed | arm | status | term. | iters | success | test metric | thr | LLM calls | tokens | cost $ | evals | first target (best) | controller outcomes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frozen_mutation | 0 | B | completed | budget_exhausted | 8 | False | 0.777 | 0.797 | 19 | 107623 | 0.0637 | 5024 | objective (optimization_workflow) | {"rejected": 1, "accepted": 1, "skipped": 6} |
| frozen_mutation | 0 | C | completed | budget_exhausted | 8 | False | 0.015 | 0.797 | 16 | 86343 | 0.0550 | 5024 | optimization_workflow (optimization_workflow) | {"rejected": 2, "no_change": 1, "skipped": 5} |
| frozen_mutation | 0 | D | completed | budget_exhausted | 4 | False | 0.358 | 0.797 | 9 | 35208 | 0.0301 | 5088 | optimization_workflow (optimization_workflow) | {"accepted": 1, "skipped": 3} |
| frozen_mutation | 1 | B | completed | budget_exhausted | 8 | False | 0.056 | 0.797 | 19 | 114612 | 0.0691 | 5024 | objective (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| frozen_mutation | 1 | C | completed | budget_exhausted | 8 | False | 0.009 | 0.797 | 21 | 128406 | 0.0725 | 5120 | planning (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| frozen_mutation | 1 | D | completed | budget_exhausted | 4 | False | 0.001 | 0.797 | 11 | 54965 | 0.0433 | 5056 | objective (optimization_workflow) | {"rejected": 1, "skipped": 3} |
| frozen_mutation | 2 | B | completed | budget_exhausted | 9 | False | 0.010 | 0.797 | 23 | 161003 | 0.0858 | 5218 | objective (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| frozen_mutation | 2 | C | completed | budget_exhausted | 9 | False | 0.148 | 0.797 | 21 | 143674 | 0.0765 | 5218 | objective (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| frozen_mutation | 2 | D | completed | budget_exhausted | 9 | True | 0.846 | 0.797 | 21 | 131201 | 0.0694 | 5250 | optimization_workflow (optimization_workflow) | {"accepted": 2, "skipped": 7} |
| offset_scorer | 0 | B | completed | budget_exhausted | 8 | True | 0.957 | 0.873 | 19 | 106410 | 0.0708 | 5024 | implementation (implementation) | {"accepted": 1, "rejected": 1, "skipped": 6} |
| offset_scorer | 0 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 18 | 123923 | 0.0775 | 5218 | optimization_workflow (implementation) | {"rejected": 2, "no_change": 1, "skipped": 6} |
| offset_scorer | 0 | D | completed | budget_exhausted | 9 | True | 0.960 | 0.873 | 21 | 125952 | 0.0777 | 5282 | implementation (implementation) | {"accepted": 2, "skipped": 7} |
| offset_scorer | 1 | B | completed | budget_exhausted | 9 | False | 0.839 | 0.873 | 20 | 118073 | 0.0656 | 5218 | implementation (implementation) | {"accepted": 1, "skipped": 8} |
| offset_scorer | 1 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 22 | 145706 | 0.0880 | 5250 | planning (implementation) | {"rejected": 2, "skipped": 7} |
| offset_scorer | 1 | D | completed | budget_exhausted | 4 | False | 0.000 | 0.873 | 11 | 51638 | 0.0468 | 5056 | implementation (implementation) | {"invalid_decision": 1, "rejected": 1, "skipped": 2} |
| offset_scorer | 2 | B | completed | budget_exhausted | 9 | True | 0.967 | 0.873 | 20 | 118664 | 0.0662 | 5250 | implementation (implementation) | {"accepted": 1, "skipped": 8} |
| offset_scorer | 2 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 25 | 149922 | 0.0824 | 5282 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| offset_scorer | 2 | D | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 20 | 133269 | 0.0796 | 5282 | objective (implementation) | {"rejected": 1, "skipped": 8} |

## Per-arm totals

| arm | runs | success | LLM calls | tokens (observed) | cost $ | oracle evals |
|---|---|---|---|---|---|---|
| B | 6 | 2 | 120 | 726385 | 0.421 | 30758 |
| C | 6 | 0 | 123 | 777974 | 0.452 | 31112 |
| D | 6 | 2 | 93 | 532233 | 0.347 | 31014 |

## Paired test-metric differences

- B-C: mean 0.572; 5 better / 1 worse of 6 pairs
- D-B: mean -0.240; 2 better / 4 worse of 6 pairs
- D-C: mean 0.332; 4 better / 2 worse of 6 pairs

By task suite (v2 = tasks seen while designing arm D; v2b_holdout = held-out):

- B-C: v3_holdout: 0.572
- D-B: v3_holdout: -0.240
- D-C: v3_holdout: 0.332

## Controller target statistics

```
{
 "B": {
  "proposals": 10,
  "target:objective": 6,
  "outcome:rejected": 6,
  "target:optimization_workflow": 1,
  "proposals_on_best_target": 4,
  "accepted": 4,
  "accepted_on_best_target": 4,
  "outcome:accepted": 4,
  "outcome:skipped": 41,
  "runs_first_proposal_on_best_target": 3,
  "runs_with_proposals": 6,
  "target:implementation": 3
 },
 "C": {
  "proposals": 14,
  "target:optimization_workflow": 4,
  "proposals_on_best_target": 3,
  "outcome:rejected": 12,
  "target:no_change": 2,
  "outcome:no_change": 2,
  "outcome:skipped": 38,
  "runs_first_proposal_on_best_target": 1,
  "runs_with_proposals": 6,
  "target:planning": 4,
  "target:objective": 3,
  "target:implementation": 1
 },
 "D": {
  "proposals": 9,
  "target:optimization_workflow": 2,
  "proposals_on_best_target": 4,
  "accepted": 5,
  "accepted_on_best_target": 3,
  "outcome:accepted": 5,
  "outcome:skipped": 30,
  "runs_first_proposal_on_best_target": 4,
  "runs_with_proposals": 6,
  "target:objective": 5,
  "outcome:rejected": 3,
  "target:implementation": 2,
  "outcome:invalid_decision": 1
 }
}
```
