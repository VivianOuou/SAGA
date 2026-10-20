"""
Summarize A/B(/C) result files into <results_dir>/ab_summary.json and ab_summary.md.

Reports per task-seed comparisons without significance tests: this is a small pilot (feasibility /
signal check only). For tasks with a known best intervention target (v2), also reports target accuracy.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

INTERVENTION_OUTCOMES = ("accepted", "rejected", "invalid_decision", "unsupported")


def fmt(x, nd=3):
    if x is None:
        return "null"
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def load_decisions(results_dir, mode, task, seed, arm):
    path = results_dir / f"{mode}__{task}__s{seed}__{arm}.decisions.jsonl"
    return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--mode", default="real_llm", choices=["real_llm", "offline_mock"])
    args = parser.parse_args()
    results_dir = Path(args.results_dir)
    rows = {}
    for f in sorted(results_dir.glob(f"{args.mode}__*__s*__[ABCDEF].json")):
        r = json.loads(f.read_text())
        rows[(r["task"], r["seed"], r["arm"])] = r
    arms = sorted({a for _, _, a in rows})
    pairs = sorted({(t, s) for t, s, _ in rows})

    table, per_arm = [], defaultdict(lambda: Counter())
    target_stats = defaultdict(lambda: Counter())
    diffs = defaultdict(list)
    reasons = Counter()
    for task, seed in pairs:
        for arm in arms:
            r = rows.get((task, seed, arm))
            if r is None:
                table.append({"task": task, "seed": seed, "arm": arm, "status": "missing"})
                continue
            mc = r.get("meta_controller") or {}
            decisions = load_decisions(results_dir, args.mode, task, seed, arm)
            proposed = [d for d in decisions if d["outcome"] in INTERVENTION_OUTCOMES + ("no_change",)]
            first = next(((d.get("decision") or {}).get("intervention_target") for d in proposed), None)
            best = r.get("best_target")
            for d in decisions:
                target = (d.get("decision") or {}).get("intervention_target")
                if d["outcome"] in INTERVENTION_OUTCOMES + ("no_change",):
                    target_stats[arm]["proposals"] += 1
                    target_stats[arm][f"target:{target}"] += 1
                    if best and target == best:
                        target_stats[arm]["proposals_on_best_target"] += 1
                if d["outcome"] == "accepted":
                    target_stats[arm]["accepted"] += 1
                    if best and target == best:
                        target_stats[arm]["accepted_on_best_target"] += 1
                if d["outcome"] in ("rejected", "invalid_decision", "unsupported", "judge_error", "controller_error"):
                    reasons[(arm, d["outcome"], d["reason"].split(":")[0][:60])] += 1
                target_stats[arm][f"outcome:{d['outcome']}"] += 1
            if best and proposed:
                target_stats[arm]["runs_first_proposal_on_best_target"] += int(first == best)
                target_stats[arm]["runs_with_proposals"] += 1
            for key in ("llm_calls", "total_tokens_observed", "cost_usd", "oracle_evals", "wall_time_s"):
                per_arm[arm][key] += r.get(key) or 0
            per_arm[arm]["runs"] += 1
            per_arm[arm]["success"] += int(bool(r.get("success")))
            table.append({
                "task": task, "seed": seed, "arm": arm, "status": r["status"], "termination": r["termination_reason"],
                "iterations": r["iterations_completed"], "success": r["success"], "test_metric": r["test_metric"],
                "threshold": r["success_threshold"], "llm_calls": r["llm_calls"], "total_tokens": r["total_tokens"],
                "tokens_observed": r.get("total_tokens_observed"), "cost_usd": r["cost_usd"], "oracle_evals": r["oracle_evals"],
                "wall_time_s": r["wall_time_s"], "best_target": best, "first_proposal_target": first,
                "outcomes": mc.get("outcomes"), "acceptance_rate": mc.get("acceptance_rate"),
            })
        for x, y in (("B", "A"), ("C", "A"), ("B", "C"), ("D", "A"), ("D", "B"), ("D", "C"),
                     ("E", "A"), ("F", "A"), ("E", "B"), ("F", "B"), ("D", "E"), ("D", "F")):
            rx, ry = rows.get((task, seed, x)), rows.get((task, seed, y))
            if rx and ry and rx["test_metric"] is not None and ry["test_metric"] is not None:
                diffs[f"{x}-{y}"].append({"task": task, "seed": seed, "suite": rx.get("suite"),
                                          "diff": rx["test_metric"] - ry["test_metric"]})

    summary = {
        "mode": args.mode,
        "note": ("REAL LLM calls on SYNTHETIC numeric tasks; small pilot, no significance testing"
                 if args.mode == "real_llm" else "MOCK planner/analyzer/judge: pipeline check only, not evidence"),
        "arms": arms,
        "rows": table,
        "per_arm_totals": {a: dict(c) for a, c in per_arm.items()},
        "paired_differences": {k: v for k, v in diffs.items()},
        "mean_paired_difference": {k: (sum(d["diff"] for d in v) / len(v)) for k, v in diffs.items() if v},
        "wins": {k: {"x_better": sum(d["diff"] > 0 for d in v), "y_better": sum(d["diff"] < 0 for d in v), "n": len(v)}
                 for k, v in diffs.items()},
        "mean_paired_difference_by_suite": {
            k: {suite: sum(d["diff"] for d in v if d["suite"] == suite) / max(1, sum(d["suite"] == suite for d in v))
                for suite in sorted({d["suite"] for d in v})}
            for k, v in diffs.items() if v},
        "target_stats": {a: dict(c) for a, c in target_stats.items()},
        "reject_or_failure_reasons": {f"{a}|{o}|{r}": n for (a, o, r), n in reasons.items()},
    }
    (results_dir / "ab_summary.json").write_text(json.dumps(summary, indent=2))

    lines = [f"# Meta-Controller A/B summary ({args.mode})", "", summary["note"], "",
             "| task | seed | arm | status | term. | iters | success | test metric | thr | LLM calls | tokens | cost $ | evals | first target (best) | controller outcomes |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        if r["status"] == "missing":
            lines.append(f"| {r['task']} | {r['seed']} | {r['arm']} | missing |" + " |" * 11)
            continue
        first = f"{r['first_proposal_target']} ({r['best_target']})" if r["best_target"] else (r["first_proposal_target"] or "")
        lines.append(f"| {r['task']} | {r['seed']} | {r['arm']} | {r['status']} | {r['termination']} | {r['iterations']} | "
                     f"{r['success']} | {fmt(r['test_metric'])} | {fmt(r['threshold'])} | {r['llm_calls']} | "
                     f"{fmt(r['total_tokens'])} | {fmt(r['cost_usd'], 4)} | {r['oracle_evals']} | {first if r['arm'] != 'A' else ''} | "
                     f"{json.dumps(r['outcomes']) if r['outcomes'] else ''} |")
    lines += ["", "## Per-arm totals", "", "| arm | runs | success | LLM calls | tokens (observed) | cost $ | oracle evals |", "|---|---|---|---|---|---|---|"]
    for a in arms:
        t = per_arm[a]
        lines.append(f"| {a} | {t['runs']} | {t['success']} | {t['llm_calls']} | {t['total_tokens_observed']} | {fmt(float(t['cost_usd']), 3)} | {t['oracle_evals']} |")
    lines += ["", "## Paired test-metric differences", ""]
    for k, v in summary["mean_paired_difference"].items():
        w = summary["wins"][k]
        lines.append(f"- {k}: mean {fmt(v)}; {w['x_better']} better / {w['y_better']} worse of {w['n']} pairs")
    lines += ["", "By task suite (v2 = tasks seen while designing arm D; v2b_holdout = held-out):", ""]
    for k, v in summary["mean_paired_difference_by_suite"].items():
        lines.append(f"- {k}: " + ", ".join(f"{suite}: {fmt(val)}" for suite, val in v.items()))
    lines += ["", "## Controller target statistics", "", "```", json.dumps(summary["target_stats"], indent=1), "```"]
    (results_dir / "ab_summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
