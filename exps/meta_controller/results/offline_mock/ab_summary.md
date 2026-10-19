# Meta-Controller A/B summary (offline_mock)

MOCK planner/analyzer/judge: pipeline check only, not evidence

| task | seed | arm | status | term. | iters | success | test metric | thr | LLM calls | tokens | cost $ | evals | wall s | controller outcomes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| constrained_yield | 0 | A | completed | max_iterations | 6 | False | 0.000 | 0.592 | 12 | 3000 | 0.0000 | 1772 | 28 |  |
| constrained_yield | 0 | B | completed | max_iterations | 6 | False | 0.579 | 0.592 | 19 | 3650 | 0.0000 | 3156 | 36 | {"accepted": 1, "no_change": 4, "skipped": 1} |
| robust_design | 0 | A | completed | max_iterations | 6 | False | 0.289 | 0.454 | 12 | 3000 | 0.0000 | 1772 | 27 |  |
| robust_design | 0 | B | completed | max_iterations | 6 | False | 0.369 | 0.454 | 17 | 3250 | 0.0000 | 3156 | 34 | {"accepted": 1, "no_change": 4, "skipped": 1} |
| spectral_signal | 0 | A | completed | max_iterations | 6 | False | 0.000 | 0.853 | 12 | 3000 | 0.0000 | 1772 | 28 |  |
| spectral_signal | 0 | B | completed | max_iterations | 6 | False | 0.779 | 0.853 | 17 | 3250 | 0.0000 | 3060 | 36 | {"accepted": 1, "no_change": 4, "skipped": 1} |

Success: A 0/3, B 0/3.
Mean paired test-metric difference (B - A): 0.479.

Controller target:outcome counts: {"planning:accepted": 1, "no_change:no_change": 12, "objective:accepted": 1, "implementation:accepted": 1}

Reject / failure reasons: {}
