# Meta-Controller A/B summary (real_llm)

REAL LLM calls on SYNTHETIC numeric tasks; small pilot, no significance testing

| task | seed | arm | status | term. | iters | success | test metric | thr | LLM calls | tokens | cost $ | evals | first target (best) | controller outcomes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| noisy_search | 0 | A | completed | budget_exhausted | 16 | False | 0.000 | 0.839 | 51 | 310949 | 0.1145 | 4830 |  |  |
| noisy_search | 0 | B | completed | budget_exhausted | 8 | False | 0.000 | 0.839 | 30 | 121990 | 0.0784 | 5148 | objective (optimization_workflow) | {"invalid_decision": 2, "rejected": 2, "skipped": 4} |
| noisy_search | 0 | C | completed | budget_exhausted | 9 | True | 0.898 | 0.839 | 31 | 128893 | 0.0726 | 5250 | optimization_workflow (optimization_workflow) | {"accepted": 1, "no_change": 1, "rejected": 1, "skipped": 6} |
| noisy_search | 1 | A | completed | budget_exhausted | 16 | False | 0.000 | 0.839 | 51 | 349987 | 0.1194 | 4860 |  |  |
| noisy_search | 1 | B | completed | budget_exhausted | 8 | False | 0.001 | 0.839 | 36 | 140078 | 0.0785 | 5086 | objective (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| noisy_search | 1 | C | completed | budget_exhausted | 8 | False | 0.002 | 0.839 | 31 | 160353 | 0.0896 | 5022 | planning (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| noisy_search | 2 | A | completed | budget_exhausted | 16 | False | 0.001 | 0.839 | 51 | 356797 | 0.1262 | 4764 |  |  |
| noisy_search | 2 | B | completed | budget_exhausted | 8 | False | 0.000 | 0.839 | 29 | 116014 | 0.0711 | 5056 | objective (optimization_workflow) | {"rejected": 2, "invalid_decision": 1, "skipped": 5} |
| noisy_search | 2 | C | completed | budget_exhausted | 9 | False | 0.004 | 0.839 | 36 | 157787 | 0.0884 | 5250 | objective (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| overflow_scorer | 0 | A | completed | budget_exhausted | 17 | False | 0.000 | 0.878 | 51 | 390651 | 0.1391 | 4962 |  |  |
| overflow_scorer | 0 | B | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 52 | 260006 | 0.1391 | 4058 | objective (implementation) | {"invalid_decision": 4, "rejected": 1, "skipped": 4} |
| overflow_scorer | 0 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 27 | 144230 | 0.0838 | 5250 | optimization_workflow (implementation) | {"rejected": 2, "no_change": 1, "skipped": 6} |
| overflow_scorer | 1 | A | completed | budget_exhausted | 14 | False | 0.000 | 0.878 | 50 | 292449 | 0.1243 | 4156 |  |  |
| overflow_scorer | 1 | B | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 32 | 154181 | 0.0913 | 5250 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| overflow_scorer | 1 | C | completed | budget_exhausted | 8 | False | 0.000 | 0.878 | 49 | 211163 | 0.1397 | 5024 | planning (implementation) | {"rejected": 2, "skipped": 6} |
| overflow_scorer | 2 | A | completed | budget_exhausted | 15 | False | 0.000 | 0.878 | 52 | 324668 | 0.1398 | 4478 |  |  |
| overflow_scorer | 2 | B | completed | budget_exhausted | 9 | True | 0.954 | 0.878 | 37 | 170107 | 0.0921 | 5218 | implementation (implementation) | {"accepted": 1, "rejected": 1, "skipped": 7} |
| overflow_scorer | 2 | C | completed | budget_exhausted | 9 | False | 0.000 | 0.878 | 38 | 192711 | 0.1060 | 5218 | objective (implementation) | {"rejected": 2, "skipped": 7} |
| stagnant_search | 0 | A | completed | budget_exhausted | 17 | False | 0.221 | 0.874 | 52 | 429016 | 0.1444 | 4962 |  |  |
| stagnant_search | 0 | B | completed | budget_exhausted | 9 | False | 0.234 | 0.874 | 30 | 137813 | 0.0791 | 5282 | objective (optimization_workflow) | {"invalid_decision": 1, "rejected": 2, "skipped": 6} |
| stagnant_search | 0 | C | completed | budget_exhausted | 9 | False | 0.866 | 0.874 | 27 | 133895 | 0.0697 | 5218 | optimization_workflow (optimization_workflow) | {"accepted": 2, "no_change": 1, "skipped": 6} |
| stagnant_search | 1 | A | completed | budget_exhausted | 17 | False | 0.201 | 0.874 | 52 | 390770 | 0.1303 | 4962 |  |  |
| stagnant_search | 1 | B | completed | budget_exhausted | 8 | False | 0.061 | 0.874 | 30 | 160621 | 0.0847 | 5088 | objective (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| stagnant_search | 1 | C | completed | budget_exhausted | 9 | False | 0.060 | 0.874 | 29 | 135150 | 0.0761 | 5218 | planning (optimization_workflow) | {"rejected": 2, "skipped": 7} |
| stagnant_search | 2 | A | completed | budget_exhausted | 17 | False | 0.167 | 0.874 | 51 | 323216 | 0.1223 | 5186 |  |  |
| stagnant_search | 2 | B | completed | budget_exhausted | 8 | False | 0.052 | 0.874 | 26 | 100739 | 0.0587 | 5120 | objective (optimization_workflow) | {"rejected": 2, "skipped": 6} |
| stagnant_search | 2 | C | completed | budget_exhausted | 9 | False | 0.062 | 0.874 | 30 | 139536 | 0.0744 | 5218 | objective (optimization_workflow) | {"rejected": 2, "skipped": 7} |

## Per-arm totals

| arm | runs | success | LLM calls | tokens (observed) | cost $ | oracle evals |
|---|---|---|---|---|---|---|
| A | 9 | 0 | 461 | 3168503 | 1.160 | 43160 |
| B | 9 | 1 | 302 | 1361549 | 0.773 | 45306 |
| C | 9 | 1 | 298 | 1403718 | 0.800 | 46668 |

## Paired test-metric differences

- B-A: mean 0.079; 3 better / 6 worse of 9 pairs
- C-A: mean 0.145; 4 better / 5 worse of 9 pairs
- B-C: mean -0.066; 2 better / 7 worse of 9 pairs

## Controller target statistics

```
{
 "B": {
  "proposals": 25,
  "target:objective": 19,
  "outcome:invalid_decision": 8,
  "outcome:rejected": 16,
  "outcome:skipped": 51,
  "runs_first_proposal_on_best_target": 1,
  "runs_with_proposals": 9,
  "target:implementation": 4,
  "proposals_on_best_target": 4,
  "target:None": 2,
  "accepted": 1,
  "accepted_on_best_target": 1,
  "outcome:accepted": 1
 },
 "C": {
  "proposals": 21,
  "target:optimization_workflow": 6,
  "proposals_on_best_target": 5,
  "accepted": 3,
  "accepted_on_best_target": 3,
  "outcome:accepted": 3,
  "target:no_change": 3,
  "outcome:no_change": 3,
  "outcome:rejected": 15,
  "outcome:skipped": 58,
  "runs_first_proposal_on_best_target": 2,
  "runs_with_proposals": 9,
  "target:planning": 6,
  "target:implementation": 3,
  "target:objective": 3
 }
}
```
