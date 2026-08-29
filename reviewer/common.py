"""Shared plumbing for invoking `claude -p` as a code reviewer and parsing
its structured verdict."""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

MODEL = "claude-sonnet-5"

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["bug", "no_bug"],
            "description": "Does this change introduce a behavioral bug?",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Self-reported confidence in the verdict.",
        },
        "evidence": {
            "type": "string",
            "description": "The concrete evidence for the verdict: a quoted "
            "test failure, a specific input/output pair, or a cited line. "
            "Must not be a restatement of the verdict itself.",
        },
        "reasoning": {
            "type": "string",
            "description": "Short explanation connecting the evidence to the verdict.",
        },
    },
    "required": ["verdict", "confidence", "evidence", "reasoning"],
    "additionalProperties": False,
}


@dataclass
class ReviewResult:
    verdict: str
    confidence: float
    evidence: str
    reasoning: str
    cost_usd: float
    duration_ms: int
    num_turns: int
    raw: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def predicted_bug(self) -> bool:
        return self.verdict == "bug"


def invoke_claude(
    prompt: str,
    *,
    cwd: Path,
    allowed_tools: Optional[List[str]] = None,
    disallowed_tools: Optional[List[str]] = None,
    add_dir: Optional[Path] = None,
    timeout: int = 120,
    _retries: int = 2,
) -> ReviewResult:
    result = _invoke_claude_once(
        prompt, cwd=cwd, allowed_tools=allowed_tools,
        disallowed_tools=disallowed_tools, add_dir=add_dir, timeout=timeout,
    )
    attempt = 1
    while result.error is not None and attempt < _retries:
        result = _invoke_claude_once(
            prompt, cwd=cwd, allowed_tools=allowed_tools,
            disallowed_tools=disallowed_tools, add_dir=add_dir, timeout=timeout,
        )
        attempt += 1
    return result


def _invoke_claude_once(
    prompt: str,
    *,
    cwd: Path,
    allowed_tools: Optional[List[str]] = None,
    disallowed_tools: Optional[List[str]] = None,
    add_dir: Optional[Path] = None,
    timeout: int = 120,
) -> ReviewResult:
    cmd = [
        "claude", "-p",
        "--model", MODEL,
        "--output-format", "json",
        "--disable-slash-commands",
        "--json-schema=" + json.dumps(VERDICT_SCHEMA),
    ]
    # NOTE: these are variadic options (`<tools...>`) — if passed as two argv
    # tokens ("--flag", "value") they greedily swallow the *next* argv token
    # too, which would eat the prompt itself. Joining with "=" keeps the
    # value in one token so the prompt survives as its own positional arg.
    if allowed_tools:
        cmd.append("--allowedTools=" + " ".join(allowed_tools))
    if disallowed_tools:
        cmd.append("--disallowedTools=" + " ".join(disallowed_tools))
    if add_dir:
        cmd.append("--add-dir=" + str(add_dir))
    cmd.append(prompt)

    start = time.time()
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
        stdin=subprocess.DEVNULL,
    )
    elapsed_ms = int((time.time() - start) * 1000)

    if proc.returncode != 0 and not proc.stdout.strip():
        return ReviewResult(
            verdict="no_bug", confidence=0.0, evidence="", reasoning="",
            cost_usd=0.0, duration_ms=elapsed_ms, num_turns=0,
            error=f"claude CLI failed: {proc.stderr[-2000:]}",
        )

    outer = json.loads(proc.stdout)
    payload = outer.get("structured_output")
    if payload is None:
        try:
            payload = json.loads(outer["result"])
        except (KeyError, json.JSONDecodeError) as exc:
            return ReviewResult(
                verdict="no_bug", confidence=0.0, evidence="", reasoning="",
                cost_usd=outer.get("total_cost_usd", 0.0),
                duration_ms=outer.get("duration_ms", elapsed_ms),
                num_turns=outer.get("num_turns", 0),
                raw=outer,
                error=f"could not parse structured result: {exc}",
            )

    return ReviewResult(
        verdict=payload["verdict"],
        confidence=float(payload["confidence"]),
        evidence=payload["evidence"],
        reasoning=payload["reasoning"],
        cost_usd=outer.get("total_cost_usd", 0.0),
        duration_ms=outer.get("duration_ms", elapsed_ms),
        num_turns=outer.get("num_turns", 0),
        raw=outer,
    )
