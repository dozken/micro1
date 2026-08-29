"""Capture a full, human-readable trajectory (every tool call and its
result) for one mutant case, for both the baseline and agent reviewers.
Used to produce the 'agent trajectories' deliverable.

Usage:
    python3 eval/capture_trajectory.py <module> <mutant_index> <out_prefix>
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"
sys.path.insert(0, str(REPO_ROOT / "reviewer"))
import agent as agent_reviewer  # noqa: E402
import baseline as baseline_reviewer  # noqa: E402
import common  # noqa: E402


def stream_invoke(prompt: str, cwd: Path, allowed_tools=None, disallowed_tools=None, add_dir=None):
    cmd = [
        "claude", "-p",
        "--model", common.MODEL,
        "--output-format", "stream-json",
        "--verbose",
        "--disable-slash-commands",
    ]
    if allowed_tools:
        cmd.append("--allowedTools=" + " ".join(allowed_tools))
    if disallowed_tools:
        cmd.append("--disallowedTools=" + " ".join(disallowed_tools))
    if add_dir:
        cmd.append("--add-dir=" + str(add_dir))
    cmd.append(prompt)
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=180)
    events = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return events


def render_markdown(title: str, prompt: str, events: list[dict]) -> str:
    lines = [f"# Trajectory: {title}\n", "## Prompt given to the agent\n", "```", prompt.strip(), "```\n"]
    lines.append("## Turn-by-turn trajectory\n")
    for ev in events:
        t = ev.get("type")
        if t == "assistant":
            for block in ev["message"]["content"]:
                if block["type"] == "text":
                    lines.append(f"**Assistant (final/interim text):**\n\n{block['text']}\n")
                elif block["type"] == "tool_use":
                    lines.append(f"**Tool call:** `{block['name']}`  input: `{json.dumps(block['input'])}`\n")
        elif t == "user":
            for block in ev["message"]["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    content = block.get("content")
                    if isinstance(content, list):
                        content = "\n".join(
                            c.get("text", "") for c in content if isinstance(c, dict)
                        )
                    content = str(content)
                    truncated = content if len(content) < 1500 else content[:1500] + "\n...[truncated]"
                    lines.append(f"**Tool result:**\n```\n{truncated}\n```\n")
        elif t == "result":
            lines.append("## Final structured output\n")
            lines.append(f"```json\n{ev.get('result', '')}\n```\n")
            lines.append(f"Cost: ${ev.get('total_cost_usd', 0):.4f} | "
                          f"Turns: {ev.get('num_turns')} | Duration: {ev.get('duration_ms')}ms\n")
    return "\n".join(lines)


def main():
    module, index, out_prefix = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    record = json.loads((REPO_ROOT / "mutants" / module / f"{index:03d}.json").read_text())
    out_dir = REPO_ROOT / "docs" / "trajectories"
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- baseline trajectory (no tools, diff only) ---
    prompt_b = baseline_reviewer.PROMPT_TEMPLATE.format(module=module, diff=record["diff"])
    with tempfile.TemporaryDirectory(prefix="traj_baseline_") as tmp:
        events_b = stream_invoke(prompt_b, Path(tmp), disallowed_tools=baseline_reviewer.NO_TOOL_LIST)
    (out_dir / f"{out_prefix}_baseline.md").write_text(
        render_markdown(f"{module} mutant #{index} ({record['description']}) — BASELINE", prompt_b, events_b)
    )

    # --- agent trajectory (tools + verification) ---
    prompt_a = agent_reviewer.PROMPT_TEMPLATE.format(module=module, diff=record["diff"])
    with tempfile.TemporaryDirectory(prefix="traj_agent_") as tmp:
        tmp_path = Path(tmp)
        for f in CORPUS_DIR.glob("*.py"):
            shutil.copy(f, tmp_path / f.name)
        (tmp_path / f"{module}.py").write_text(record["mutated_source"])
        events_a = stream_invoke(prompt_a, tmp_path, allowed_tools=agent_reviewer.ALLOWED_TOOLS, add_dir=tmp_path)
    (out_dir / f"{out_prefix}_agent.md").write_text(
        render_markdown(f"{module} mutant #{index} ({record['description']}) — AGENT", prompt_a, events_a)
    )
    print(f"Wrote {out_dir}/{out_prefix}_baseline.md and {out_prefix}_agent.md")


if __name__ == "__main__":
    main()
