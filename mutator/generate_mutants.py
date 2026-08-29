"""Generate mutants for every corpus module, run each mutant's test suite in
an isolated copy, and classify it as 'killed' (a test caught it) or
'survived' (all tests still pass despite the injected bug).

Usage:
    python3 mutator/generate_mutants.py [--out mutants]

Output: mutants/<module>/<index>.json with the mutation metadata, unified
diff, and test verdict; mutants/summary.json with counts per module.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ast  # noqa: E402
from engine import apply_mutation, diff, enumerate_mutations  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"

MODULES = [
    "interval_merge",
    "lru_ttl_cache",
    "token_bucket",
    "signup_validator",
]


def run_tests_against(module_name: str, mutated_source: str) -> dict:
    """Copy the corpus dir to a temp workspace, swap in the mutated module,
    run its pytest file, and report pass/fail plus captured output."""
    with tempfile.TemporaryDirectory(prefix="mutant_") as tmp:
        tmp_path = Path(tmp)
        for f in CORPUS_DIR.glob("*.py"):
            shutil.copy(f, tmp_path / f.name)
        (tmp_path / f"{module_name}.py").write_text(mutated_source)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", f"test_{module_name}.py"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "returncode": proc.returncode,
            "passed": proc.returncode == 0,
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-15:]),
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO_ROOT / "mutants"))
    ap.add_argument("--limit-per-module", type=int, default=None,
                     help="cap mutants generated per module (default: all)")
    args = ap.parse_args()

    out_dir = Path(args.out)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    summary = {}
    for module in MODULES:
        src_path = CORPUS_DIR / f"{module}.py"
        original = src_path.read_text()
        canonical_original = ast.unparse(ast.parse(original))
        mutations = enumerate_mutations(original)
        if args.limit_per_module:
            mutations = mutations[: args.limit_per_module]

        module_out = out_dir / module
        module_out.mkdir(parents=True)
        killed = 0
        survived = 0
        for m in mutations:
            mutated_source = apply_mutation(original, m.index)
            if mutated_source == original:
                continue  # mutation was a no-op (e.g. cancels itself out)
            test_result = run_tests_against(module, mutated_source)
            verdict = "killed" if not test_result["passed"] else "survived"
            if verdict == "killed":
                killed += 1
            else:
                survived += 1
            record = {
                "module": module,
                "index": m.index,
                "kind": m.kind,
                "variant": m.variant,
                "lineno": m.lineno,
                "description": m.description,
                "verdict": verdict,
                "test_result": test_result,
                "mutated_source": mutated_source,
                "diff": diff(canonical_original, mutated_source, f"{module}.py"),
            }
            (module_out / f"{m.index:03d}.json").write_text(json.dumps(record, indent=2))

        summary[module] = {
            "total_mutations": len(mutations),
            "killed": killed,
            "survived": survived,
        }
        print(f"{module}: {len(mutations)} mutations -> {killed} killed, {survived} survived")

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nWrote mutants to {out_dir}")


if __name__ == "__main__":
    main()
