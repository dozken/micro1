"""Agentic reviewer: same verdict task as the baseline, but given tools —
it can read the full module (not just the diff) and run the actual test
suite — and is explicitly instructed to verify its claim against real
execution output before finalizing, rather than reasoning from the diff
alone."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ReviewResult, invoke_claude  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"

PROMPT_TEMPLATE = """You are reviewing a code change to a small Python utility module in this
directory. Here is the unified diff of the change:

```diff
{diff}
```

You have two tools available: Read (to read any file in this directory,
including the full module and its existing test file) and Bash, restricted
to running `python3 -m pytest`.

Do not just reason from the diff. Before giving your final verdict:
1. Read the full mutated module ({module}.py) to understand the change in context.
2. Run the existing test suite (`python3 -m pytest -q test_{module}.py`) and
   quote the actual pass/fail output — do not guess or paraphrase what you
   expect it to say.
3. If all tests pass, that does not automatically mean there is no bug —
   the test suite may simply not cover the changed behavior. Reason about
   whether the change could still misbehave on inputs the tests don't
   exercise, and say so explicitly.

Give your verdict, confidence, the concrete evidence (quote real pytest
output and/or a specific input/output pair you reasoned through), and your
reasoning.
"""

ALLOWED_TOOLS = ["Read", "Bash(python3 -m pytest*)"]


def review(module: str, mutated_source: str, diff_text: str) -> ReviewResult:
    with tempfile.TemporaryDirectory(prefix="agent_review_") as tmp:
        tmp_path = Path(tmp)
        for f in CORPUS_DIR.glob("*.py"):
            shutil.copy(f, tmp_path / f.name)
        (tmp_path / f"{module}.py").write_text(mutated_source)

        prompt = PROMPT_TEMPLATE.format(module=module, diff=diff_text)
        return invoke_claude(
            prompt,
            cwd=tmp_path,
            allowed_tools=ALLOWED_TOOLS,
            add_dir=tmp_path,
            timeout=150,
        )


if __name__ == "__main__":
    import json

    record = json.load(open(sys.argv[1]))
    result = review(record["module"], record["mutated_source"], record["diff"])
    print(result)
