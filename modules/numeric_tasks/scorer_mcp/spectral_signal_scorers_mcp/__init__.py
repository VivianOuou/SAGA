# --- auto-generated scorers start ---
scorers: dict = {'signal_mean_level': {'function_name': 'score_signal_mean_level',
                       'description': 'Mean value of the 12 signal samples, in [0, 1].',
                       'tool_description': 'Mean level of each signal.',
                       'type': 'candidate-wise'},
 'smoothness': {'function_name': 'score_smoothness',
                'description': 'Signal smoothness in [0, 1]; higher means smoother (fewer abrupt changes between '
                               'consecutive samples).',
                'tool_description': 'Smoothness of each signal.',
                'type': 'candidate-wise'},
 'smoothness_v2': {'function_name': 'score_smoothness_v2',
                   'description': 'Signal smoothness in [0, 1] computed as exp(-sum of squared second differences / '
                                  '2.0); 1 means perfectly linear (smoothest). Higher is better.',
                   'tool_description': 'Smoothness of each signal (second-difference based).',
                   'type': 'candidate-wise'},
 'spectrum_match': {'function_name': 'score_spectrum_match',
                    'description': "Match between the signal's low-frequency magnitude spectrum (DC and harmonics 1-4) "
                                   'and the target spectrum, in [0, 1] (exp(-squared error / 0.01)). 1 means a perfect '
                                   'match. Higher is better.',
                    'tool_description': 'Spectral match of each 12-sample signal (JSON array of floats in [0, 1]).',
                    'type': 'candidate-wise'}}
# --- auto-generated scorers end ---
