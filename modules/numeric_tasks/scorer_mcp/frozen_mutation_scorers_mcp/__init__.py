# --- auto-generated scorers start ---
scorers: dict = {'distance_from_center': {'function_name': 'score_distance_from_center',
                          'description': 'Normalized Euclidean distance of the design from the center point (0.5, ..., '
                                         '0.5), in [0, 0.5].',
                          'tool_description': 'Distance from the center of the design space.',
                          'type': 'candidate-wise'},
 'parameter_spread': {'function_name': 'score_parameter_spread',
                      'description': 'Standard deviation of the 8 design parameters, in [0, 0.5].',
                      'tool_description': 'Spread of the design parameters.',
                      'type': 'candidate-wise'},
 'performance': {'function_name': 'score_performance',
                 'description': 'Device performance in [0, 1] at the design point. Higher is better.',
                 'tool_description': 'Performance of each design (JSON array of 8 floats in [0, 1]).',
                 'type': 'candidate-wise'}}
# --- auto-generated scorers end ---
