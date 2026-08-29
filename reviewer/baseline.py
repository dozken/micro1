"""Simple baseline reviewer: one direct prompt, the diff only, no tools, no
test execution. This is the 'reasonable basic way to handle the task before
using the agent solution' the brief asks for."""
from __future__ import annotations

import tempfile
from pathlib import Path

from common import ReviewResult, invoke_claude

PROMPT_TEMPLATE = """You are reviewing a code change to a small Python utility module.
Below is the unified diff of the change. You do NOT have access to the repository,
you cannot run code, and you cannot read any other file. Judge only from the diff text.

Module: {module}.py

```diff
{diff}
```

Does this change introduce a behavioral bug? Give your verdict, confidence,
the concrete evidence for it (quote the specific line(s) and explain the
concrete input that would misbehave), and your reasoning.
"""

NO_TOOL_LIST = [
    "Read", "Write", "Edit", "Bash", "Glob", "Grep",
    "Task", "WebFetch", "WebSearch", "NotebookEdit",
]


def review(module: str, diff_text: str) -> ReviewResult:
    prompt = PROMPT_TEMPLATE.format(module=module, diff=diff_text)
    with tempfile.TemporaryDirectory(prefix="baseline_") as tmp:
        return invoke_claude(
            prompt,
            cwd=Path(tmp),
            disallowed_tools=NO_TOOL_LIST,
            timeout=90,
        )


if __name__ == "__main__":
    import sys
    diff = sys.stdin.read()
    result = review(sys.argv[1] if len(sys.argv) > 1 else "module", diff)
    print(result)
