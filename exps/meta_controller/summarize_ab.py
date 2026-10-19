"""
Summarize A/B result files into <results_dir>/ab_summary.json and ab_summary.md.

Reports per task-seed pairs (A vs B) without significance tests: with 3 tasks x 2 seeds this is a
feasibility / signal check only.
"""

import argparse
import json
from collections import Counter
from pathlib import Path


def fmt(x, nd=3):
    if x is None:
        return "null"
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--mode", default="real_llm", choices=["real_llm", "offline_mock"])
    args = parser.parse_args()
    results_dir = Path(args.results_dir)
    rows = {}
    for f in sorted(results_dir.glob(f"{args.mode}__*__s*__[AB].json")):
        r = json.loads(f.read_text())
        rows[(r["task"], r["seed"], r["arm"])] = r
    pairs = sorted({(t, s) for t, s, _ in rows})

    table, diffs = [], []
    targets, outcomes, reasons = Counter(), Counter(), Counter()
    for task, seed in pairs:
        a, b = rows.get((task, seed, "A")), rows.get((task, seed, "B"))
        for arm, r in (("A", a), ("B", b)):
            if r is None:
                table.append({"task": task, "seed": seed, "arm": arm, "status": "missing"})
                continue
            mc = r.get("meta_controller") or {}
            table.append({
                "task": task, "seed": seed, "arm": arm, "status": r["status"], "termination": r["termination_reason"],
                "iterations": r["iterations_completed"], "success": r["success"], "test_metric": r["test_metric"],
                "threshold": r["success_threshold"], "llm_calls": r["llm_calls"], "total_tokens": r["total_tokens"],
                "tokens_observed": r["total_tokens_observed"], "cost_usd": r["cost_usd"], "oracle_evals": r["oracle_evals"],
                "wall_time_s": r["wall_time_s"], "outcomes": mc.get("outcomes"), "by_target": mc.get("by_target"),
                "acceptance_rate": mc.get("acceptance_rate"),
            })
        if a and b and a["test_metric"] is not None and b["test_metric"] is not None:
            diffs.append({"task": task, "seed": seed, "test_metric_B_minus_A": b["test_metric"] - a["test_metric"],
                          "success_A": a["success"], "success_B": b["success"]})
        if b:
            decisions = results_dir / f"{args.mode}__{task}__s{seed}__B.decisions.jsonl"
            if decisions.exists():
                for line in decisions.read_text().splitlines():
                    d = json.loads(line)
                    target = (d.get("decision") or {}).get("intervention_target")
                    outcomes[d["outcome"]] += 1
                    if target:
                        targets[(target, d["outcome"])] += 1
                    if d["outcome"] in ("rejected", "invalid_decision", "unsupported", "judge_error", "controller_error"):
                        reasons[d["reason"].split(":")[0]] += 1

    summary = {
        "mode": args.mode,
        "note": ("REAL LLM calls on SYNTHETIC numeric tasks; small pilot, no significance testing"
                 if args.mode == "real_llm" else "MOCK planner/analyzer/judge: pipeline check only, not evidence"),
        "rows": table,
        "paired_differences": diffs,
        "success_counts": {"A": sum(1 for r in table if r.get("arm") == "A" and r.get("success")),
                           "B": sum(1 for r in table if r.get("arm") == "B" and r.get("success")),
                           "pairs": len(pairs)},
        "mean_test_metric_diff_B_minus_A": (sum(d["test_metric_B_minus_A"] for d in diffs) / len(diffs)) if diffs else None,
        "controller_outcomes": dict(outcomes),
        "controller_target_outcomes": {f"{t}:{o}": n for (t, o), n in targets.items()},
        "controller_reject_or_failure_reasons": dict(reasons),
    }
    (results_dir / "ab_summary.json").write_text(json.dumps(summary, indent=2))

    lines = [f"# Meta-Controller A/B summary ({args.mode})", "", summary["note"], "",
             "| task | seed | arm | status | term. | iters | success | test metric | thr | LLM calls | tokens | cost $ | evals | wall s | controller outcomes |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        if r["status"] == "missing":
            lines.append(f"| {r['task']} | {r['seed']} | {r['arm']} | missing | | | | | | | | | | | |")
            continue
        lines.append(f"| {r['task']} | {r['seed']} | {r['arm']} | {r['status']} | {r['termination']} | {r['iterations']} | "
                     f"{r['success']} | {fmt(r['test_metric'])} | {fmt(r['threshold'])} | {r['llm_calls']} | "
                     f"{fmt(r['total_tokens'])} | {fmt(r['cost_usd'], 4)} | {r['oracle_evals']} | {fmt(r['wall_time_s'], 0)} | "
                     f"{json.dumps(r['outcomes']) if r['outcomes'] else ''} |")
    lines += ["", f"Success: A {summary['success_counts']['A']}/{len(pairs)}, B {summary['success_counts']['B']}/{len(pairs)}.",
              f"Mean paired test-metric difference (B - A): {fmt(summary['mean_test_metric_diff_B_minus_A'])}.",
              "", "Controller target:outcome counts: " + json.dumps(summary["controller_target_outcomes"]),
              "", "Reject / failure reasons: " + json.dumps(summary["controller_reject_or_failure_reasons"])]
    (results_dir / "ab_summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
