"""Regenerate each numeric-task MCP module's __init__.py scorer table from its base.Scorer class.

Usage (repository root): python -m modules.numeric_tasks.scorer_mcp.generate_inits
"""

import importlib
import pprint
from pathlib import Path

MODULES = ["robust_design_scorers_mcp", "constrained_yield_scorers_mcp", "spectral_signal_scorers_mcp"]
FILTERS = {"within_cost_budget"}


def main():
    here = Path(__file__).resolve().parent
    for module in MODULES:
        base = importlib.import_module(f"modules.numeric_tasks.scorer_mcp.{module}.base")
        scorers = {}
        for name, info in base.Scorer().get_available_scorers().items():
            scorers[name] = {
                "function_name": info["function_name"],
                "description": info["description"],
                "tool_description": info["tool_description"],
                "type": "filter" if name in FILTERS else ("population-wise" if info["population_wise"] else "candidate-wise"),
            }
        body = ("# --- auto-generated scorers start ---\nscorers: dict = "
                + pprint.pformat(scorers, width=120, sort_dicts=False) + "\n# --- auto-generated scorers end ---\n")
        (here / module / "__init__.py").write_text(body)
        print(module, sorted(scorers))


if __name__ == "__main__":
    main()
