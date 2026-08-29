"""Evaluate the baseline and agentic reviewers on the same set of mutants.

Ground truth comes from the mutator's own test run, already computed by
generate_mutants.py: a "killed" mutant is a real, test-detectable behavior
change (ground truth = bug); a "survived" mutant passed the full existing
test suite unchanged (ground truth = no_bug, i.e. not a detectable
regression given this test suite — this includes both truly harmless
mutations and genuine equivalent mutants; see README for the caveat).

Usage:
    python3 eval/run_eval.py [--killed-per-module N] [--survived-per-module N] [--workers N]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "reviewer"))
sys.path.insert(0, str(REPO_ROOT / "mutator"))

import agent as agent_reviewer  # noqa: E402
import baseline as baseline_reviewer  # noqa: E402

MUTANTS_DIR = REPO_ROOT / "mutants"
RESULTS_DIR = REPO_ROOT / "results"
MODULES = ["interval_merge", "lru_ttl_cache", "token_bucket", "signup_validator"]


def load_mutants(module: str) -> list[dict]:
    files = sorted((MUTANTS_DIR / module).glob("*.json"))
    return [json.loads(f.read_text()) for f in files]


def select_cases(killed_per_module: int, survived_per_module: int) -> list[dict]:
    cases = []
    for module in MODULES:
        mutants = load_mutants(module)
        killed = [m for m in mutants if m["verdict"] == "killed"]
        survived = [m for m in mutants if m["verdict"] == "survived"]
        cases += killed[:killed_per_module]
        cases += survived[:survived_per_module]
    return cases


def run_case(case: dict) -> dict:
    module, diff_text = case["module"], case["diff"]
    ground_truth = "bug" if case["verdict"] == "killed" else "no_bug"

    b = baseline_reviewer.review(module, diff_text)
    a = agent_reviewer.review(module, case["mutated_source"], diff_text)

    return {
        "module": module,
        "mutation_index": case["index"],
        "mutation_kind": case["kind"],
        "description": case["description"],
        "ground_truth_verdict": ground_truth,
        "ground_truth_test_outcome": case["verdict"],
        "baseline": {
            "verdict": b.verdict, "confidence": b.confidence,
            "evidence": b.evidence, "reasoning": b.reasoning,
            "cost_usd": b.cost_usd, "duration_ms": b.duration_ms, "error": b.error,
        },
        "agent": {
            "verdict": a.verdict, "confidence": a.confidence,
            "evidence": a.evidence, "reasoning": a.reasoning,
            "cost_usd": a.cost_usd, "duration_ms": a.duration_ms,
            "num_turns": a.num_turns, "error": a.error,
        },
        "baseline_correct": b.verdict == ground_truth,
        "agent_correct": a.verdict == ground_truth,
    }


def metrics(results: list[dict], key: str) -> dict:
    tp = sum(1 for r in results if r["ground_truth_verdict"] == "bug" and r[key]["verdict"] == "bug")
    fp = sum(1 for r in results if r["ground_truth_verdict"] == "no_bug" and r[key]["verdict"] == "bug")
    fn = sum(1 for r in results if r["ground_truth_verdict"] == "bug" and r[key]["verdict"] == "no_bug")
    tn = sum(1 for r in results if r["ground_truth_verdict"] == "no_bug" and r[key]["verdict"] == "no_bug")
    n = len(results)
    accuracy = (tp + tn) / n if n else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    total_cost = sum(r[key]["cost_usd"] for r in results)
    total_ms = sum(r[key]["duration_ms"] for r in results)
    errors = sum(1 for r in results if r[key]["error"])
    return {
        "n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "accuracy": round(accuracy, 3), "precision": round(precision, 3),
        "recall": round(recall, 3), "f1": round(f1, 3),
        "total_cost_usd": round(total_cost, 4),
        "avg_duration_ms": round(total_ms / n) if n else 0,
        "errors": errors,
    }


def to_markdown(summary: dict) -> str:
    lines = ["# Evaluation Results\n"]
    lines.append(f"Cases evaluated: {summary['baseline']['n']}\n")
    lines.append("| Metric | Baseline (single prompt, no tools) | Agent (tools + verification) |")
    lines.append("|---|---|---|")
    b, a = summary["baseline"], summary["agent"]
    for label, key in [
        ("Accuracy", "accuracy"), ("Precision", "precision"), ("Recall", "recall"),
        ("F1", "f1"), ("False positives (flagged a non-bug)", "fp"),
        ("False negatives (missed a real bug)", "fn"),
        ("Total cost (USD)", "total_cost_usd"), ("Avg latency (ms)", "avg_duration_ms"),
        ("CLI/parse errors", "errors"),
    ]:
        lines.append(f"| {label} | {b[key]} | {a[key]} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--killed-per-module", type=int, default=3)
    ap.add_argument("--survived-per-module", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    if not MUTANTS_DIR.exists():
        print("mutants/ not found — run `python3 mutator/generate_mutants.py` first.", file=sys.stderr)
        sys.exit(1)

    cases = select_cases(args.killed_per_module, args.survived_per_module)
    print(f"Running {len(cases)} cases x 2 reviewers with {args.workers} workers...")

    start = time.time()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, result in enumerate(pool.map(run_case, cases)):
            results.append(result)
            print(f"  [{i+1}/{len(cases)}] {result['module']} #{result['mutation_index']} "
                  f"({result['ground_truth_verdict']}) -> baseline={result['baseline']['verdict']} "
                  f"agent={result['agent']['verdict']}")

    elapsed = time.time() - start
    summary = {
        "baseline": metrics(results, "baseline"),
        "agent": metrics(results, "agent"),
        "wall_clock_seconds": round(elapsed, 1),
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "eval_results.json").write_text(
        json.dumps({"summary": summary, "cases": results}, indent=2)
    )
    (RESULTS_DIR / "RESULTS.md").write_text(to_markdown(summary))

    print("\n" + to_markdown(summary))
    print(f"Wall clock: {elapsed:.1f}s. Wrote results/eval_results.json and results/RESULTS.md")


if __name__ == "__main__":
    main()
