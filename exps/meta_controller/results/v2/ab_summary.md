# Meta-Controller A/B summary (real_llm)

REAL LLM calls on SYNTHETIC numeric tasks; small pilot, no significance testing

| task | seed | arm | status | term. | iters | success | test metric | thr | LLM calls | tokens | cost $ | evals | first target (best) | controller outcomes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| noisy_search | 0 | A | completed | budget_exhausted | 16 | False | 0.000 | 0.839 | 51 | 310949 | 0.1145 | 4830 |  |  |
| noisy_search | 0 | B | completed | budget_exhausted | 8 | False | 0.000 | 0.839 | 30 | 121990 | 0.0784 | 5148 | objective (optimization_workflow) | {"invalid_decision": 2, "rejected": 2, "skipped": 4} |
| noisy_search | 0 | C | completed | budget_exhausted | 9 | True | 0.898 | 0.839 | 31 | 128893 | 0.0726 | 5250 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 1, "rejected": 1, "skipped": 6} |
| noisy_search | 0 | D | completed | budget_exhausted | 8 | False | 0.004 | 0.839 | 28 | 116054 | 0.0746 | 5008 | optimization_workflow (optimization_workflow) | {"invalid_decision": 2, "rejected": 2, "skipped": 4} |
| noisy_search | 1 | A | completed | budget_exhausted | 16 | False | 0.000 | 0.839 | 51 | 349987 | 0.1194 | 4860 |  |  |
| noisy_search | 1 | B | completed | budget_exhausted | 8 | False | 0.001 | 0.839 | 36 | 140078 | 0.0785 | 5086 | objective (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| noisy_search | 1 | C | completed | budget_exhausted | 8 | False | 0.002 | 0.839 | 31 | 160353 | 0.0896 | 5022 | planning (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| noisy_search | 1 | D | completed | budget_exhausted | 8 | False | 0.679 | 0.839 | 26 | 105244 | 0.0635 | 5087 | objective (optimization_workflow) | {"rejected": 1, "accepted": 1, "skipped": 6} |
| noisy_search | 2 | A | completed | budget_exhausted | 16 | False | 0.001 | 0.839 | 51 | 356797 | 0.1262 | 4764 |  |  |
| noisy_search | 2 | B | completed | budget_exhausted | 8 | False | 0.000 | 0.839 | 29 | 116014 | 0.0711 | 5056 | objective (optimization_workflow) | {"rejected": 2, "invalid_decision": 1, "skipped": 5} |
| noisy_search | 2 | C | completed | budget_exhausted | 9 | False | 0.004 | 0.839 | 36 | 157787 | 0.0884 | 5250 | objective (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| noisy_search | 2 | D | completed | budget_exhausted | 8 | False | 0.000 | 0.839 | 34 | 180726 | 0.0995 | 5146 | optimization_workflow (optimization_workflow) | {"invalid_decision": 1, "rejected": 2, "skipped": 5} |
| overflow_scorer | 0 | A | completed | budget_exhausted | 17 | False | 0.000 | 0.878 | 51 | 390651 | 0.1391 | 4962 |  |  |
| overflow_scorer | 0 | B | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 52 | 260006 | 0.1391 | 4058 | objective (implementation) | {"invalid_decision": 4, "rejected": 1, "skipped": 4} |
| overflow_scorer | 0 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 27 | 144230 | 0.0838 | 5250 | optimization_workflow (implementation) | {"rejected": 2, "no_change": 1, "skipped": 6} |
| overflow_scorer | 0 | D | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 31 | 164656 | 0.0917 | 5250 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| overflow_scorer | 1 | A | completed | budget_exhausted | 14 | False | 0.000 | 0.878 | 50 | 292449 | 0.1243 | 4156 |  |  |
| overflow_scorer | 1 | B | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 32 | 154181 | 0.0913 | 5250 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| overflow_scorer | 1 | C | completed | budget_exhausted | 8 | False | 0.000 | 0.878 | 49 | 211163 | 0.1397 | 5024 | planning (implementation) | {"rejected": 2, "skipped": 6} |
| overflow_scorer | 1 | D | completed | budget_exhausted | 9 | True | 0.960 | 0.878 | 35 | 169447 | 0.0899 | 5250 | implementation (implementation) | {"accepted": 1, "rejected": 1, "skipped": 7} |
| overflow_scorer | 2 | A | completed | budget_exhausted | 15 | False | 0.000 | 0.878 | 52 | 324668 | 0.1398 | 4478 |  |  |
| overflow_scorer | 2 | B | completed | budget_exhausted | 9 | True | 0.954 | 0.878 | 37 | 170107 | 0.0921 | 5218 | implementation (implementation) | {"accepted": 1, "rejected": 1, "skipped": 7} |
| overflow_scorer | 2 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 38 | 192711 | 0.1060 | 5218 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| overflow_scorer | 2 | D | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 34 | 212658 | 0.1066 | 5250 | objective (implementation) | {"invalid_decision": 1, "rejected": 2, "skipped": 6} |
| stagnant_search | 0 | A | completed | budget_exhausted | 17 | False | 0.221 | 0.874 | 52 | 429016 | 0.1444 | 4962 |  |  |
| stagnant_search | 0 | B | completed | budget_exhausted | 9 | False | 0.234 | 0.874 | 30 | 137813 | 0.0791 | 5282 | objective (optimization_workflow) | {"invalid_decision": 1, "rejected": 2, "skipped": 6} |
| stagnant_search | 0 | C | completed | budget_exhausted | 9 | False | 0.866 | 0.874 | 27 | 133895 | 0.0697 | 5218 | optimization_workflow (optimization_workflow) | {"accepted": 2, "no_change": 1, "skipped": 6} |
| stagnant_search | 0 | D | completed | budget_exhausted | 9 | True | 0.967 | 0.874 | 32 | 145816 | 0.0821 | 5282 | optimization_workflow (optimization_workflow) | {"invalid_decision": 2, "accepted": 2, "skipped": 5} |
| stagnant_search | 1 | A | completed | budget_exhausted | 17 | False | 0.201 | 0.874 | 52 | 390770 | 0.1303 | 4962 |  |  |
| stagnant_search | 1 | B | completed | budget_exhausted | 8 | False | 0.061 | 0.874 | 30 | 160621 | 0.0847 | 5088 | objective (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| stagnant_search | 1 | C | completed | budget_exhausted | 9 | False | 0.060 | 0.874 | 29 | 135150 | 0.0761 | 5218 | planning (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| stagnant_search | 1 | D | completed | budget_exhausted | 9 | False | 0.043 | 0.874 | 32 | 154320 | 0.0848 | 5218 | optimization_workflow (optimization_workflow) | {"invalid_decision": 2, "rejected": 2, "skipped": 5} |
| stagnant_search | 2 | A | completed | budget_exhausted | 17 | False | 0.167 | 0.874 | 51 | 323216 | 0.1223 | 5186 |  |  |
| stagnant_search | 2 | B | completed | budget_exhausted | 8 | False | 0.052 | 0.874 | 26 | 100739 | 0.0587 | 5120 | objective (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| stagnant_search | 2 | C | completed | budget_exhausted | 9 | False | 0.062 | 0.874 | 30 | 139536 | 0.0744 | 5218 | objective (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| stagnant_search | 2 | D | completed | budget_exhausted | 8 | True | 0.960 | 0.874 | 27 | 120744 | 0.0712 | 5024 | optimization_workflow (optimization_workflow) | {"accepted": 2, "skipped": 6} |
| underflow_cost | 0 | A | failed | error | 8 | False | 0.000 | 0.867 | 35 | 135385 | 0.0855 | 2416 |  |  |
| underflow_cost | 0 | B | completed | budget_exhausted | 8 | True | 0.903 | 0.867 | 31 | 124906 | 0.0730 | 5024 | implementation (implementation) | {"accepted": 2, "skipped": 6} |
| underflow_cost | 0 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.867 | 35 | 197166 | 0.0970 | 5250 | optimization_workflow (implementation) | {"rejected": 2, "no_change": 1, "skipped": 6} |
| underflow_cost | 0 | D | completed | budget_exhausted | 9 | False | 0.000 | 0.867 | 32 | 157140 | 0.0839 | 5250 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| underflow_cost | 1 | A | completed | budget_exhausted | 14 | False | 0.000 | 0.867 | 51 | 387089 | 0.1392 | 4124 |  |  |
| underflow_cost | 1 | B | completed | budget_exhausted | 9 | False | 0.000 | 0.867 | 35 | 161248 | 0.0902 | 5218 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| underflow_cost | 1 | C | completed | budget_exhausted | 8 | False | 0.000 | 0.867 | 31 | 139480 | 0.0895 | 5056 | planning (implementation) | {"rejected": 2, "skipped": 6} |
| underflow_cost | 1 | D | completed | budget_exhausted | 9 | False | 0.000 | 0.867 | 45 | 283530 | 0.1520 | 5250 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| underflow_cost | 2 | A | completed | budget_exhausted | 16 | False | 0.000 | 0.867 | 50 | 395068 | 0.1402 | 4672 |  |  |
| underflow_cost | 2 | B | completed | budget_exhausted | 9 | True | 0.953 | 0.867 | 30 | 153232 | 0.0827 | 5218 | objective (implementation) | {"rejected": 1, "accepted": 1, "skipped": 7} |
| underflow_cost | 2 | C | completed | budget_exhausted | 8 | False | 0.000 | 0.867 | 30 | 149021 | 0.0875 | 5056 | objective (implementation) | {"rejected": 2, "skipped": 6} |
| underflow_cost | 2 | D | completed | budget_exhausted | 9 | True | 0.941 | 0.867 | 40 | 168494 | 0.1007 | 5288 | implementation (implementation) | {"accepted": 1, "invalid_decision": 1, "rejected": 1, "skipped": 6} |

## Per-arm totals

| arm | runs | success | LLM calls | tokens (observed) | cost $ | oracle evals |
|---|---|---|---|---|---|---|
| A | 12 | 0 | 597 | 4086045 | 1.525 | 54372 |
| B | 12 | 3 | 398 | 1800935 | 1.019 | 60766 |
| C | 12 | 1 | 394 | 1889385 | 1.074 | 62030 |
| D | 12 | 4 | 396 | 1978829 | 1.100 | 62303 |

## Paired test-metric differences

- B-A: mean 0.214; 5 better / 7 worse of 12 pairs
- C-A: mean 0.108; 4 better / 8 worse of 12 pairs
- B-C: mean 0.106; 5 better / 7 worse of 12 pairs
- D-A: mean 0.330; 7 better / 5 worse of 12 pairs
- D-B: mean 0.116; 7 better / 5 worse of 12 pairs
- D-C: mean 0.222; 7 better / 5 worse of 12 pairs

By task suite (v2 = tasks seen while designing arm D; v2b_holdout = held-out):

- B-A: v2: 0.079, v2b_holdout: 0.619
- C-A: v2: 0.145, v2b_holdout: -0.000
- B-C: v2: -0.066, v2b_holdout: 0.619
- D-A: v2: 0.336, v2b_holdout: 0.314
- D-B: v2: 0.257, v2b_holdout: -0.305
- D-C: v2: 0.191, v2b_holdout: 0.314

## Controller target statistics

```
{
 "B": {
  "proposals": 31,
  "target:objective": 23,
  "outcome:invalid_decision": 8,
  "outcome:rejected": 19,
  "outcome:skipped": 71,
  "runs_first_proposal_on_best_target": 2,
  "runs_with_proposals": 12,
  "target:implementation": 6,
  "proposals_on_best_target": 6,
  "target:None": 2,
  "accepted": 4,
  "accepted_on_best_target": 3,
  "outcome:accepted": 4
 },
 "C": {
  "proposals": 28,
  "target:optimization_workflow": 8,
  "proposals_on_best_target": 5,
  "accepted": 3,
  "accepted_on_best_target": 3,
  "outcome:accepted": 3,
  "target:no_change": 4,
  "outcome:no_change": 4,
  "outcome:rejected": 21,
  "outcome:skipped": 76,
  "runs_first_proposal_on_best_target": 2,
  "runs_with_proposals": 12,
  "target:planning": 8,
  "target:implementation": 3,
  "target:objective": 5
 },
 "D": {
  "proposals": 33,
  "target:optimization_workflow": 14,
  "proposals_on_best_target": 18,
  "outcome:invalid_decision": 9,
  "target:objective": 12,
  "outcome:rejected": 17,
  "outcome:skipped": 71,
  "runs_first_proposal_on_best_target": 7,
  "runs_with_proposals": 12,
  "accepted": 7,
  "accepted_on_best_target": 5,
  "outcome:accepted": 7,
  "target:planning": 2,
  "target:implementation": 5
 }
}
```
