#!/usr/bin/env python3
"""
Entry point used by SAGA's McpScorerManager: python -m <this package> --local --transport streamable-http --port P

These synthetic numeric-task scorers are pure numpy; only local mode (run_scorers_in_docker=False) is provided.
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Synthetic numeric-task MCP scorer server (local mode only)")
    parser.add_argument("--local", action="store_true", help="Run the server in this Python environment")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="streamable-http")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--no-gpu", action="store_true", help="Ignored (accepted for interface compatibility)")
    args = parser.parse_args()
    if not args.local:
        sys.exit("This synthetic scorer module only supports --local (set run_scorers_in_docker=False).")
    from .mcp_server import run_server
    run_server(args.transport, args.host, args.port)


if __name__ == "__main__":
    main()
