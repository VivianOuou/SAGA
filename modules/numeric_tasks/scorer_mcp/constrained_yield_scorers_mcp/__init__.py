# --- auto-generated scorers start ---
scorers: dict = {'cost_budget_slack': {'function_name': 'score_cost_budget_slack',
                       'description': 'Budget slack 0.15 - cost, in [-0.85, 0.15]. Negative values mean the design is '
                                      'over budget. Larger means more slack.',
                       'tool_description': 'Remaining budget.',
                       'type': 'candidate-wise'},
 'production_cost': {'function_name': 'score_production_cost',
                     'description': 'Normalized production cost in [0, 1] (weighted sum of squared allocation levels). '
                                    'The hard budget is cost <= 0.15. Lower is cheaper.',
                     'tool_description': 'Normalized production cost.',
                     'type': 'candidate-wise'},
 'within_cost_budget': {'function_name': 'score_within_cost_budget',
                        'description': 'Filter: passes (1.0) if the normalized production cost is <= 0.15 (the hard '
                                       'budget), fails (0.0) otherwise.',
                        'tool_description': 'Budget feasibility filter.',
                        'type': 'filter'},
 'yield_estimate': {'function_name': 'score_yield_estimate',
                    'description': 'Expected production yield in [0, 1] under nominal market conditions (weighted sum '
                                   'of square roots of the allocation levels, normalized). Higher is better.',
                    'tool_description': 'Nominal yield of each allocation (JSON array of 6 floats in [0, 1]).',
                    'type': 'candidate-wise'},
 'yield_per_unit_cost': {'function_name': 'score_yield_per_unit_cost',
                         'description': 'Production efficiency: nominal yield divided by (cost + 0.05). Higher means '
                                        'more yield per unit cost.',
                         'tool_description': 'Yield per unit cost.',
                         'type': 'candidate-wise'}}
# --- auto-generated scorers end ---
