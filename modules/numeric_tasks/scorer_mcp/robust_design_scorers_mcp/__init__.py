# --- auto-generated scorers start ---
scorers: dict = {'center_distance': {'function_name': 'score_center_distance',
                     'description': 'Normalized Euclidean distance of the design from the center point (0.5, ..., '
                                    '0.5), in [0, 0.5].',
                     'tool_description': 'Distance from the center of the design space.',
                     'type': 'candidate-wise'},
 'cliff_margin': {'function_name': 'score_cliff_margin',
                  'description': 'Signed Euclidean distance of the design to the failure boundary x0 + x1 = 1.0, in '
                                 '[-0.71, 0.71]. Positive values are inside the safe region; larger means safer.',
                  'tool_description': 'Signed distance to the failure boundary.',
                  'type': 'candidate-wise'},
 'nominal_performance': {'function_name': 'score_nominal_performance',
                         'description': 'Nominal device performance in [0, 1], evaluated exactly at the design '
                                        'parameters (no manufacturing tolerance). Designs beyond the failure boundary '
                                        'x0 + x1 > 1.0 score 0. Higher is better.',
                         'tool_description': 'Nominal performance of each design (JSON array of 8 floats in [0, 1]).',
                         'type': 'candidate-wise'},
 'robust_performance_mc': {'function_name': 'score_robust_performance_mc',
                           'description': 'Monte-Carlo estimate (16 fixed tolerance samples, independent Gaussian '
                                          'deviation with std 0.08 per parameter) of the expected device performance '
                                          'in [0, 1] under manufacturing tolerances. Noisy but unbiased estimate. '
                                          'Higher is better.',
                           'tool_description': 'Monte-Carlo expected performance under tolerance noise.',
                           'type': 'candidate-wise'}}
# --- auto-generated scorers end ---
