# Meta-Controller A/B summary (real_llm)

REAL LLM calls on SYNTHETIC numeric tasks; small pilot, no significance testing

| task | seed | arm | status | term. | iters | success | test metric | thr | LLM calls | tokens | cost $ | evals | first target (best) | controller outcomes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frozen_mutation | 0 | A | completed | budget_exhausted | 17 | False | 0.042 | 0.797 | 35 | 373803 | 0.1345 | 5026 |  |  |
| frozen_mutation | 0 | B | completed | budget_exhausted | 8 | False | 0.018 | 0.797 | 18 | 98371 | 0.0634 | 5068 | objective (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| frozen_mutation | 0 | C | completed | budget_exhausted | 9 | False | 0.018 | 0.797 | 20 | 140904 | 0.0728 | 5282 | optimization_workflow (optimization_workflow) | {"rejected": 2, "no_change": 1, "skipped": 6} |
| frozen_mutation | 0 | D | completed | budget_exhausted | 9 | False | 0.737 | 0.797 | 20 | 128962 | 0.0780 | 5250 | optimization_workflow (optimization_workflow) | {"accepted": 2, "skipped": 7} |
| frozen_mutation | 0 | E | completed | budget_exhausted | 9 | False | 0.774 | 0.797 | 20 | 113814 | 0.0708 | 5282 | optimization_workflow (optimization_workflow) | {"accepted": 1, "rejected": 1, "skipped": 7} |
| frozen_mutation | 0 | F | completed | budget_exhausted | 8 | False | 0.702 | 0.797 | 18 | 93253 | 0.0595 | 5024 | optimization_workflow (optimization_workflow) | {"accepted": 2, "skipped": 6} |
| frozen_mutation | 1 | A | completed | budget_exhausted | 17 | False | 0.001 | 0.797 | 37 | 393780 | 0.1304 | 5058 |  |  |
| frozen_mutation | 1 | B | completed | budget_exhausted | 8 | True | 0.814 | 0.797 | 19 | 100242 | 0.0647 | 5036 | optimization_workflow (optimization_workflow) | {"rejected": 1, "invalid_decision": 1, "accepted": 1, "skipped": 5} |
| frozen_mutation | 1 | C | completed | budget_exhausted | 9 | False | 0.014 | 0.797 | 24 | 173789 | 0.0927 | 5250 | planning (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| frozen_mutation | 1 | D | completed | budget_exhausted | 9 | False | 0.791 | 0.797 | 20 | 127213 | 0.0744 | 5218 | objective (optimization_workflow) | {"rejected": 1, "accepted": 1, "skipped": 7} |
| frozen_mutation | 1 | E | completed | budget_exhausted | 9 | True | 0.813 | 0.797 | 21 | 136745 | 0.0784 | 5250 | optimization_workflow (optimization_workflow) | {"accepted": 2, "skipped": 7} |
| frozen_mutation | 1 | F | completed | budget_exhausted | 8 | False | 0.795 | 0.797 | 18 | 93282 | 0.0594 | 5088 | optimization_workflow (optimization_workflow) | {"accepted": 1, "rejected": 1, "skipped": 6} |
| frozen_mutation | 2 | A | completed | budget_exhausted | 18 | False | 0.010 | 0.797 | 37 | 441378 | 0.1655 | 5284 |  |  |
| frozen_mutation | 2 | B | completed | budget_exhausted | 8 | False | 0.338 | 0.797 | 18 | 96286 | 0.0629 | 5024 | objective (optimization_workflow) | {"rejected": 1, "accepted": 1, "skipped": 6} |
| frozen_mutation | 2 | C | completed | budget_exhausted | 8 | False | 0.075 | 0.797 | 21 | 147061 | 0.0815 | 5024 | objective (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| frozen_mutation | 2 | D | completed | budget_exhausted | 8 | False | 0.000 | 0.797 | 18 | 90100 | 0.0562 | 5020 | optimization_workflow (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| frozen_mutation | 2 | E | completed | budget_exhausted | 9 | False | 0.655 | 0.797 | 21 | 138913 | 0.0754 | 5250 | objective (optimization_workflow) | {"rejected": 1, "accepted": 1, "skipped": 7} |
| frozen_mutation | 2 | F | completed | budget_exhausted | 9 | False | 0.729 | 0.797 | 20 | 128051 | 0.0793 | 5250 | optimization_workflow (optimization_workflow) | {"accepted": 2, "skipped": 7} |
| offset_scorer | 0 | A | completed | budget_exhausted | 18 | False | 0.000 | 0.873 | 36 | 430603 | 0.1646 | 5252 |  |  |
| offset_scorer | 0 | B | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 22 | 129062 | 0.0731 | 5282 | implementation (implementation) | {"rejected": 2, "invalid_decision": 1, "skipped": 6} |
| offset_scorer | 0 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 20 | 148360 | 0.0830 | 5218 | optimization_workflow (implementation) | {"rejected": 2, "no_change": 1, "skipped": 6} |
| offset_scorer | 0 | D | completed | budget_exhausted | 9 | True | 0.955 | 0.873 | 25 | 133003 | 0.0828 | 5249 | implementation (implementation) | {"accepted": 1, "rejected": 1, "skipped": 7} |
| offset_scorer | 0 | E | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 25 | 155705 | 0.0955 | 5218 | implementation (implementation) | {"rejected": 2, "skipped": 7} |
| offset_scorer | 0 | F | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 31 | 176439 | 0.1066 | 5282 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| offset_scorer | 1 | A | completed | budget_exhausted | 17 | False | 0.000 | 0.873 | 35 | 378551 | 0.1446 | 5026 |  |  |
| offset_scorer | 1 | B | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 25 | 149009 | 0.0839 | 5250 | implementation (implementation) | {"rejected": 2, "skipped": 7} |
| offset_scorer | 1 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 21 | 127296 | 0.0766 | 5282 | planning (implementation) | {"rejected": 2, "skipped": 7} |
| offset_scorer | 1 | D | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 21 | 125220 | 0.0770 | 5218 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| offset_scorer | 1 | E | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 23 | 161707 | 0.0951 | 5218 | implementation (implementation) | {"rejected": 2, "invalid_decision": 1, "skipped": 6} |
| offset_scorer | 1 | F | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 27 | 187828 | 0.1039 | 5282 | implementation (implementation) | {"invalid_decision": 1, "rejected": 2, "skipped": 6} |
| offset_scorer | 2 | A | completed | budget_exhausted | 18 | False | 0.000 | 0.873 | 36 | 411665 | 0.1529 | 5252 |  |  |
| offset_scorer | 2 | B | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 33 | 175226 | 0.1167 | 5250 | implementation (implementation) | {"rejected": 2, "skipped": 7} |
| offset_scorer | 2 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 22 | 156265 | 0.0820 | 5250 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| offset_scorer | 2 | D | completed | budget_exhausted | 9 | True | 0.963 | 0.873 | 21 | 125535 | 0.0698 | 5250 | implementation (implementation) | {"accepted": 2, "skipped": 7} |
| offset_scorer | 2 | E | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 22 | 164011 | 0.0996 | 5250 | implementation (implementation) | {"invalid_decision": 1, "rejected": 2, "skipped": 6} |
| offset_scorer | 2 | F | completed | budget_exhausted | 9 | False | 0.000 | 0.873 | 32 | 172878 | 0.1019 | 5250 | objective (implementation) | {"rejected": 2, "skipped": 7} |

## Per-arm totals

| arm | runs | success | LLM calls | tokens (observed) | cost $ | oracle evals |
|---|---|---|---|---|---|---|
| A | 6 | 0 | 216 | 2429780 | 0.893 | 30898 |
| B | 6 | 1 | 135 | 748196 | 0.465 | 30910 |
| C | 6 | 0 | 128 | 893675 | 0.489 | 31306 |
| D | 6 | 2 | 125 | 730033 | 0.438 | 31205 |
| E | 6 | 1 | 132 | 870895 | 0.515 | 31468 |
| F | 6 | 0 | 146 | 851731 | 0.510 | 31176 |

## Paired test-metric differences

- B-A: mean 0.186; 4 better / 2 worse of 6 pairs
- C-A: mean 0.009; 5 better / 1 worse of 6 pairs
- B-C: mean 0.177; 4 better / 1 worse of 6 pairs
- D-A: mean 0.566; 5 better / 1 worse of 6 pairs
- D-B: mean 0.379; 4 better / 2 worse of 6 pairs
- D-C: mean 0.557; 5 better / 1 worse of 6 pairs
- E-A: mean 0.365; 6 better / 0 worse of 6 pairs
- F-A: mean 0.362; 5 better / 1 worse of 6 pairs
- E-B: mean 0.179; 3 better / 3 worse of 6 pairs
- F-B: mean 0.176; 3 better / 3 worse of 6 pairs
- D-E: mean 0.201; 3 better / 3 worse of 6 pairs
- D-F: mean 0.203; 4 better / 2 worse of 6 pairs

By task suite (v2 = tasks seen while designing arm D; v2b_holdout = held-out):

- B-A: v3_holdout: 0.186
- C-A: v3_holdout: 0.009
- B-C: v3_holdout: 0.177
- D-A: v3_holdout: 0.566
- D-B: v3_holdout: 0.379
- D-C: v3_holdout: 0.557
- E-A: v3_holdout: 0.365
- F-A: v3_holdout: 0.362
- E-B: v3_holdout: 0.179
- F-B: v3_holdout: 0.176
- D-E: v3_holdout: 0.201
- D-F: v3_holdout: 0.203

## Controller target statistics

```
{
 "B": {
  "proposals": 14,
  "target:objective": 4,
  "outcome:rejected": 10,
  "target:optimization_workflow": 4,
  "proposals_on_best_target": 9,
  "outcome:skipped": 37,
  "runs_first_proposal_on_best_target": 4,
  "runs_with_proposals": 6,
  "target:implementation": 6,
  "outcome:invalid_decision": 2,
  "accepted": 2,
  "accepted_on_best_target": 2,
  "outcome:accepted": 2
 },
 "C": {
  "proposals": 14,
  "target:optimization_workflow": 4,
  "proposals_on_best_target": 3,
  "outcome:rejected": 12,
  "target:no_change": 2,
  "outcome:no_change": 2,
  "outcome:skipped": 39,
  "runs_first_proposal_on_best_target": 1,
  "runs_with_proposals": 6,
  "target:planning": 4,
  "target:implementation": 2,
  "target:objective": 2
 },
 "D": {
  "proposals": 12,
  "target:optimization_workflow": 4,
  "proposals_on_best_target": 6,
  "accepted": 6,
  "accepted_on_best_target": 4,
  "outcome:accepted": 6,
  "target:objective": 6,
  "outcome:skipped": 41,
  "runs_first_proposal_on_best_target": 4,
  "runs_with_proposals": 6,
  "outcome:rejected": 6,
  "target:implementation": 2
 },
 "E": {
  "proposals": 14,
  "target:optimization_workflow": 3,
  "proposals_on_best_target": 9,
  "accepted": 4,
  "accepted_on_best_target": 3,
  "outcome:accepted": 4,
  "target:objective": 5,
  "outcome:rejected": 8,
  "outcome:skipped": 40,
  "runs_first_proposal_on_best_target": 5,
  "runs_with_proposals": 6,
  "target:implementation": 6,
  "outcome:invalid_decision": 2
 },
 "F": {
  "proposals": 13,
  "target:optimization_workflow": 3,
  "proposals_on_best_target": 8,
  "accepted": 5,
  "accepted_on_best_target": 3,
  "outcome:accepted": 5,
  "target:objective": 5,
  "outcome:skipped": 39,
  "runs_first_proposal_on_best_target": 4,
  "runs_with_proposals": 6,
  "outcome:rejected": 7,
  "target:implementation": 5,
  "outcome:invalid_decision": 1
 }
}
```
