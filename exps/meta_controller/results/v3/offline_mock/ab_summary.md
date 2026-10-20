# Meta-Controller A/B summary (offline_mock)

MOCK planner/analyzer/judge: pipeline check only, not evidence

| task | seed | arm | status | term. | iters | success | test metric | thr | LLM calls | tokens | cost $ | evals | first target (best) | controller outcomes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frozen_mutation | 0 | A | completed | budget_exhausted | 18 | False | 0.186 | 0.797 | 36 | 9000 | 0.0000 | 5252 |  |  |
| frozen_mutation | 0 | B | completed | budget_exhausted | 13 | True | 0.853 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| frozen_mutation | 0 | C | completed | budget_exhausted | 9 | False | 0.186 | 0.797 | 18 | 4500 | 0.0000 | 5218 | optimization_workflow (optimization_workflow) | {"rejected": 2, "no_change": 1, "skipped": 6} |
| frozen_mutation | 0 | D | completed | budget_exhausted | 13 | True | 0.853 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| frozen_mutation | 0 | E | completed | budget_exhausted | 13 | True | 0.853 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| frozen_mutation | 0 | F | completed | budget_exhausted | 13 | True | 0.853 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| frozen_mutation | 1 | A | completed | budget_exhausted | 18 | False | 0.052 | 0.797 | 36 | 9000 | 0.0000 | 5252 |  |  |
| frozen_mutation | 1 | B | completed | budget_exhausted | 13 | True | 0.823 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| frozen_mutation | 1 | C | completed | budget_exhausted | 9 | False | 0.052 | 0.797 | 20 | 4900 | 0.0000 | 5282 | planning (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| frozen_mutation | 1 | D | completed | budget_exhausted | 13 | True | 0.823 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| frozen_mutation | 1 | E | completed | budget_exhausted | 13 | True | 0.823 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| frozen_mutation | 1 | F | completed | budget_exhausted | 13 | True | 0.823 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| frozen_mutation | 2 | A | completed | budget_exhausted | 18 | False | 0.203 | 0.797 | 36 | 9000 | 0.0000 | 5252 |  |  |
| frozen_mutation | 2 | B | completed | budget_exhausted | 13 | True | 0.815 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| frozen_mutation | 2 | C | completed | budget_exhausted | 9 | False | 0.203 | 0.797 | 20 | 4900 | 0.0000 | 5218 | objective (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| frozen_mutation | 2 | D | completed | budget_exhausted | 13 | True | 0.815 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| frozen_mutation | 2 | E | completed | budget_exhausted | 13 | True | 0.815 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| frozen_mutation | 2 | F | completed | budget_exhausted | 13 | True | 0.815 | 0.797 | 32 | 6800 | 0.0000 | 5090 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 0 | A | completed | budget_exhausted | 18 | False | 0.000 | 0.873 | 36 | 9000 | 0.0000 | 5252 |  |  |
| offset_scorer | 0 | B | completed | budget_exhausted | 13 | True | 0.966 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 0 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 18 | 4500 | 0.0000 | 5218 | optimization_workflow (implementation) | {"rejected": 2, "no_change": 1, "skipped": 6} |
| offset_scorer | 0 | D | completed | budget_exhausted | 13 | True | 0.966 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 0 | E | completed | budget_exhausted | 13 | True | 0.966 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 0 | F | completed | budget_exhausted | 13 | True | 0.966 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 1 | A | completed | budget_exhausted | 18 | False | 0.000 | 0.873 | 36 | 9000 | 0.0000 | 5252 |  |  |
| offset_scorer | 1 | B | completed | budget_exhausted | 13 | True | 0.967 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 1 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 20 | 4900 | 0.0000 | 5282 | planning (implementation) | {"rejected": 2, "skipped": 7} |
| offset_scorer | 1 | D | completed | budget_exhausted | 13 | True | 0.967 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 1 | E | completed | budget_exhausted | 13 | True | 0.967 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 1 | F | completed | budget_exhausted | 13 | True | 0.967 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 2 | A | completed | budget_exhausted | 18 | False | 0.000 | 0.873 | 36 | 9000 | 0.0000 | 5252 |  |  |
| offset_scorer | 2 | B | completed | budget_exhausted | 13 | True | 0.953 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 2 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 20 | 4900 | 0.0000 | 5218 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| offset_scorer | 2 | D | completed | budget_exhausted | 13 | True | 0.953 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 2 | E | completed | budget_exhausted | 13 | True | 0.953 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |
| offset_scorer | 2 | F | completed | budget_exhausted | 13 | True | 0.953 | 0.873 | 32 | 6800 | 0.0000 | 5090 | implementation (implementation) | {"accepted": 1, "no_change": 5, "skipped": 7} |

## Per-arm totals

| arm | runs | success | LLM calls | tokens (observed) | cost $ | oracle evals |
|---|---|---|---|---|---|---|
| A | 6 | 0 | 216 | 54000 | 0.000 | 31512 |
| B | 6 | 6 | 192 | 40800 | 0.000 | 30540 |
| C | 6 | 0 | 116 | 28600 | 0.000 | 31436 |
| D | 6 | 6 | 192 | 40800 | 0.000 | 30540 |
| E | 6 | 6 | 192 | 40800 | 0.000 | 30540 |
| F | 6 | 6 | 192 | 40800 | 0.000 | 30540 |

## Paired test-metric differences

- B-A: mean 0.822; 6 better / 0 worse of 6 pairs
- C-A: mean 0.000; 2 better / 1 worse of 6 pairs
- B-C: mean 0.822; 6 better / 0 worse of 6 pairs
- D-A: mean 0.822; 6 better / 0 worse of 6 pairs
- D-B: mean 0.000; 0 better / 0 worse of 6 pairs
- D-C: mean 0.822; 6 better / 0 worse of 6 pairs
- E-A: mean 0.822; 6 better / 0 worse of 6 pairs
- F-A: mean 0.822; 6 better / 0 worse of 6 pairs
- E-B: mean 0.000; 0 better / 0 worse of 6 pairs
- F-B: mean 0.000; 0 better / 0 worse of 6 pairs
- D-E: mean 0.000; 0 better / 0 worse of 6 pairs
- D-F: mean 0.000; 0 better / 0 worse of 6 pairs

By task suite (v2 = tasks seen while designing arm D; v2b_holdout = held-out):

- B-A: v3_holdout: 0.822
- C-A: v3_holdout: 0.000
- B-C: v3_holdout: 0.822
- D-A: v3_holdout: 0.822
- D-B: v3_holdout: 0.000
- D-C: v3_holdout: 0.822
- E-A: v3_holdout: 0.822
- F-A: v3_holdout: 0.822
- E-B: v3_holdout: 0.000
- F-B: v3_holdout: 0.000
- D-E: v3_holdout: 0.000
- D-F: v3_holdout: 0.000

## Controller target statistics

```
{
 "B": {
  "proposals": 36,
  "target:optimization_workflow": 3,
  "proposals_on_best_target": 6,
  "accepted": 6,
  "accepted_on_best_target": 6,
  "outcome:accepted": 6,
  "target:no_change": 30,
  "outcome:no_change": 30,
  "outcome:skipped": 42,
  "runs_first_proposal_on_best_target": 6,
  "runs_with_proposals": 6,
  "target:implementation": 3
 },
 "C": {
  "proposals": 14,
  "target:optimization_workflow": 4,
  "proposals_on_best_target": 2,
  "outcome:rejected": 12,
  "target:no_change": 2,
  "outcome:no_change": 2,
  "outcome:skipped": 40,
  "runs_first_proposal_on_best_target": 1,
  "runs_with_proposals": 6,
  "target:planning": 4,
  "target:objective": 4
 },
 "D": {
  "proposals": 36,
  "target:optimization_workflow": 3,
  "proposals_on_best_target": 6,
  "accepted": 6,
  "accepted_on_best_target": 6,
  "outcome:accepted": 6,
  "target:no_change": 30,
  "outcome:no_change": 30,
  "outcome:skipped": 42,
  "runs_first_proposal_on_best_target": 6,
  "runs_with_proposals": 6,
  "target:implementation": 3
 },
 "E": {
  "proposals": 36,
  "target:optimization_workflow": 3,
  "proposals_on_best_target": 6,
  "accepted": 6,
  "accepted_on_best_target": 6,
  "outcome:accepted": 6,
  "target:no_change": 30,
  "outcome:no_change": 30,
  "outcome:skipped": 42,
  "runs_first_proposal_on_best_target": 6,
  "runs_with_proposals": 6,
  "target:implementation": 3
 },
 "F": {
  "proposals": 36,
  "target:optimization_workflow": 3,
  "proposals_on_best_target": 6,
  "accepted": 6,
  "accepted_on_best_target": 6,
  "outcome:accepted": 6,
  "target:no_change": 30,
  "outcome:no_change": 30,
  "outcome:skipped": 42,
  "runs_first_proposal_on_best_target": 6,
  "runs_with_proposals": 6,
  "target:implementation": 3
 }
}
```
