# Meta-Controller A/B summary (real_llm)

REAL LLM calls on SYNTHETIC numeric tasks; small pilot, no significance testing

| task | seed | arm | status | term. | iters | success | test metric | thr | LLM calls | tokens | cost $ | evals | wall s | controller outcomes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| constrained_yield | 0 | A | completed | max_iterations | 6 | True | 0.647 | 0.592 | 18 | 73668 | 0.0490 | 1836 | 355 |  |
| constrained_yield | 0 | B | completed | max_iterations | 6 | True | 0.650 | 0.592 | 22 | 95765 | 0.0728 | 7180 | 498 | {"rejected": 4, "skipped": 2} |
| constrained_yield | 1 | A | completed | max_iterations | 6 | True | 0.603 | 0.592 | 18 | 71340 | 0.0498 | 1836 | 256 |  |
| constrained_yield | 1 | B | completed | max_iterations | 6 | True | 0.648 | 0.592 | 23 | 98721 | 0.0701 | 5860 | 522 | {"accepted": 1, "rejected": 2, "invalid_decision": 2, "skipped": 1} |
| robust_design | 0 | A | completed | max_iterations | 6 | False | 0.442 | 0.454 | 19 | 91918 | 0.0601 | 1772 | 297 |  |
| robust_design | 0 | B | completed | max_iterations | 6 | False | 0.451 | 0.454 | 24 | 111900 | 0.0788 | 5892 | 407 | {"invalid_decision": 2, "rejected": 2, "accepted": 1, "skipped": 1} |
| robust_design | 1 | A | completed | max_iterations | 6 | False | 0.431 | 0.454 | 19 | 92164 | 0.0583 | 1900 | 291 |  |
| robust_design | 1 | B | completed | max_iterations | 6 | False | 0.450 | 0.454 | 23 | 102701 | 0.0710 | 7180 | 525 | {"accepted": 1, "rejected": 3, "skipped": 2} |
| spectral_signal | 0 | A | completed | max_iterations | 6 | False | 0.824 | 0.853 | 21 | 113471 | 0.0606 | 1804 | 364 |  |
| spectral_signal | 0 | B | completed | max_iterations | 6 | False | 0.816 | 0.853 | 22 | 92618 | 0.0629 | 7052 | 351 | {"accepted": 2, "rejected": 2, "skipped": 2} |
| spectral_signal | 1 | A | completed | max_iterations | 6 | False | 0.801 | 0.853 | 18 | 77036 | 0.0493 | 1804 | 264 |  |
| spectral_signal | 1 | B | completed | max_iterations | 6 | False | 0.847 | 0.853 | 22 | 87841 | 0.0590 | 7020 | 333 | {"accepted": 2, "rejected": 2, "skipped": 2} |

Success: A 2/6, B 2/6.
Mean paired test-metric difference (B - A): 0.019.

Controller target:outcome counts: {"objective:rejected": 15, "objective:accepted": 5, "objective:invalid_decision": 2, "implementation:invalid_decision": 1, "implementation:accepted": 2}

Reject / failure reasons: {"no_improvement": 15, "'within_cost_budget' is already an objective": 1, "objective is already bound to this scorer": 1, "proposed_change for 'objective'": 1, "'robust_performance_mc' is already an objective": 1}
