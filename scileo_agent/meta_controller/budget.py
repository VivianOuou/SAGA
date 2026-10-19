"""
Budget and cost accounting shared by the opt-in budget guard and the Meta-Controller.

Coverage (read before trusting the numbers):
- LLM calls / tokens / cost are summed from every LLMClient handed to the tracker. A client that
  is shared by several callers (e.g. the planner client also used for planning trials) is counted
  once, so nothing is double counted.
- `call_count` in LLMClient counts successful completions only. Attempts that raised and were
  retried by LLMClient are not counted as calls (they usually carry no token usage either).
- Responses without a `usage` block are counted in `calls_missing_usage`; whenever that number is
  non-zero the corresponding token total is reported as None (unknown), never as 0.
- Usage merged in by nested agents (coding agent, candidate analyzer) adds tokens/cost without
  incrementing `call_count`.
- Oracle evaluations are only known when the optimizer exposes `num_evaluations`; otherwise None.
"""

import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


CAP_TO_USAGE = {
    "max_llm_calls": "llm_calls",
    "max_total_tokens": "total_tokens_observed",
    "max_oracle_evals": "oracle_evals",
    "max_wall_time_s": "wall_time_s",
    "max_cost_usd": "cost_usd",
}


def _client_counters(client) -> Dict[str, Any]:
    stats = client.get_stats() if hasattr(client, "get_stats") else {}
    out = {"calls": 0, "tokens": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0}
    for model_stats in stats.values():
        out["calls"] += model_stats.get("call_count", 0) or 0
        out["tokens"] += model_stats.get("total_tokens", 0) or 0
        out["input_tokens"] += model_stats.get("input_tokens", 0) or 0
        out["output_tokens"] += model_stats.get("output_tokens", 0) or 0
        out["cost"] += model_stats.get("cost", 0.0) or 0.0
    responses = getattr(client, "responses", None) or []
    out["missing_usage"] = sum(1 for r in responses if isinstance(r, dict) and not r.get("usage"))
    return out


def _dedupe(clients: Iterable) -> List:
    seen, unique = set(), []
    for client in clients:
        if client is None or id(client) in seen:
            continue
        seen.add(id(client))
        unique.append(client)
    return unique


class BudgetTracker:
    """Tracks consumption against optional caps (same caps are given to every arm of an A/B)."""

    def __init__(
        self,
        caps: Optional[Dict[str, float]],
        client_provider: Callable[[], Iterable],
        eval_provider: Callable[[], Optional[int]],
    ):
        unknown = set(caps or {}) - set(CAP_TO_USAGE)
        if unknown:
            raise ValueError(f"Unknown budget caps: {sorted(unknown)}. Allowed: {sorted(CAP_TO_USAGE)}")
        self.caps = {k: v for k, v in (caps or {}).items() if v is not None}
        self._client_provider = client_provider
        self._eval_provider = eval_provider
        self._t0 = time.monotonic()

    # ------------------------------------------------------------------ snapshots
    def snapshot(self) -> Dict[str, Any]:
        clients = _dedupe(self._client_provider())
        return {
            "clients": {id(c): _client_counters(c) for c in clients},
            "evals": self._eval_provider(),
            "time": time.monotonic(),
        }

    @staticmethod
    def delta(before: Dict[str, Any], after: Dict[str, Any], extra_evals: Optional[int] = None) -> Dict[str, Any]:
        """Cost between two snapshots. Clients that appear only in `after` start from zero."""
        zero = {"calls": 0, "tokens": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0, "missing_usage": 0}
        total = dict(zero)
        for cid, now in after["clients"].items():
            then = before["clients"].get(cid, zero)
            for key in total:
                total[key] += now[key] - then[key]
        evals = None
        if after["evals"] is not None and before["evals"] is not None:
            evals = after["evals"] - before["evals"]
        if extra_evals is not None:
            evals = (evals or 0) + extra_evals
        return {
            "llm_calls": total["calls"],
            "total_tokens": total["tokens"] if total["missing_usage"] == 0 else None,
            "total_tokens_observed_lower_bound": total["tokens"],
            "input_tokens": total["input_tokens"] if total["missing_usage"] == 0 else None,
            "output_tokens": total["output_tokens"] if total["missing_usage"] == 0 else None,
            "calls_missing_usage": total["missing_usage"],
            "cost_usd": round(total["cost"], 6),
            "oracle_evals": evals,
            "wall_time_s": round(after["time"] - before["time"], 3),
        }

    # ------------------------------------------------------------------ totals
    def usage(self) -> Dict[str, Any]:
        snap = self.snapshot()
        calls = sum(c["calls"] for c in snap["clients"].values())
        tokens = sum(c["tokens"] for c in snap["clients"].values())
        missing = sum(c["missing_usage"] for c in snap["clients"].values())
        cost = sum(c["cost"] for c in snap["clients"].values())
        return {
            "llm_calls": calls,
            "total_tokens": tokens if missing == 0 else None,
            "total_tokens_observed": tokens,
            "calls_missing_usage": missing,
            "cost_usd": round(cost, 6),
            "oracle_evals": snap["evals"],
            "wall_time_s": round(snap["time"] - self._t0, 3),
        }

    def remaining(self, usage: Optional[Dict[str, Any]] = None) -> Dict[str, Optional[float]]:
        usage = usage or self.usage()
        out = {}
        for cap_key, cap in self.caps.items():
            used = usage.get(CAP_TO_USAGE[cap_key])
            out[cap_key] = None if used is None else cap - used
        return out

    def exhausted(self) -> Tuple[bool, Optional[str]]:
        usage = self.usage()
        for cap_key, cap in self.caps.items():
            used = usage.get(CAP_TO_USAGE[cap_key])
            if used is not None and used >= cap:
                return True, f"{cap_key}={cap} reached (used {used})"
        return False, None

    def can_afford(self, estimate: Dict[str, float]) -> Tuple[bool, Optional[str]]:
        """`estimate` uses usage keys (llm_calls, total_tokens_observed, oracle_evals, ...)."""
        usage = self.usage()
        for cap_key, cap in self.caps.items():
            usage_key = CAP_TO_USAGE[cap_key]
            used = usage.get(usage_key)
            need = estimate.get(usage_key)
            if used is None or need is None:
                continue
            if used + need > cap:
                return False, f"{cap_key}: used {used} + estimated {need} > cap {cap}"
        return True, None

    def report(self) -> Dict[str, Any]:
        usage = self.usage()
        return {"caps": dict(self.caps), "used": usage, "remaining": self.remaining(usage)}
