# --- auto-generated scorers start ---
scorers: dict = {'design_cost': {'function_name': 'score_design_cost',
                 'description': 'Normalized design cost in [0, 1]. Lower is better.',
                 'tool_description': 'Cost of each design (JSON array of 8 floats in [0, 1]).',
                 'type': 'candidate-wise'},
 'parameter_mean': {'function_name': 'score_parameter_mean',
                    'description': 'Mean of the 8 design parameters, in [0, 1].',
                    'tool_description': 'Mean of the design parameters.',
                    'type': 'candidate-wise'},
 'parameter_spread': {'function_name': 'score_parameter_spread',
                      'description': 'Standard deviation of the 8 design parameters, in [0, 0.5].',
                      'tool_description': 'Spread of the design parameters.',
                      'type': 'candidate-wise'}}
# --- auto-generated scorers end ---
