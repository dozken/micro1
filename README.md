# Can an agent catch the bugs a careless AI-driven refactor introduces?

A small, reproducible benchmark comparing a naive single-prompt code
reviewer against a tool-using, verification-driven agentic reviewer, on
the specific job of catching subtle bugs in a code change.

## Who has this problem

Engineering teams that let AI coding agents open PRs (refactors, small
features, dependency bumps) now have a review bottleneck: a human still
has to decide whether the diff is safe to merge, but the volume of
agent-authored changes is growing faster than reviewer attention. The
failure mode that matters most is not "the code doesn't run" — CI catches
that — it's the **silent** regression: a boundary flipped, an operator
swapped, a condition inverted, in a way that still passes the existing
tests and looks like a reasonable diff on its face.

**The bottleneck:** a reviewer (human or agent) skimming a diff has no
way to tell a cosmetic rewrite from a subtly broken one without actually
running the code. Confident-sounding, diff-only judgments — "yes this
looks fine" / "yes this is a bug" — are exactly as reliable as the
reviewer's ability to mentally execute the change, which for boundary and
off-by-one conditions is poor even for careful humans.

**Does the agent solve it well, and can someone reproduce that claim?**
That's what this repo measures: a fixed, deterministic set of injected
bugs, a fair baseline given the same task, and a full eval anyone can
re-run from a clean environment (see below).

## What existed before this project vs. what was built

**Existed already:** Python 3.11, `pytest`, and the `claude` CLI
(Claude Code, already authenticated in this environment) — no new
libraries, services, or API keys were introduced.

**Built for this submission:** everything under `corpus/`, `mutator/`,
`reviewer/`, `eval/`, `results/`, and `docs/trajectories/` — a synthetic
test corpus, a deterministic bug-injection engine, two reviewer
implementations (baseline and agent), an evaluation harness, and the
recorded results/trajectories from running it.

## Architecture

```
corpus/    4 hand-written single-file Python utility modules + pytest suites
             (interval_merge, lru_ttl_cache, token_bucket, signup_validator)
mutator/   engine.py: deterministic AST mutation engine (6 rule types)
           generate_mutants.py: applies every mutation, runs the module's
             own test suite in an isolated temp copy, labels each mutant
             "killed" (a test caught it) or "survived" (silent)
reviewer/  common.py: shared claude -p invocation + strict JSON-schema verdict
           baseline.py: ONE prompt, the diff text only, all tools disallowed
           agent.py: sandboxed temp copy of the mutated module + its tests,
             Read + Bash(pytest-only), explicitly instructed to run the real
             suite and quote its output rather than reason from the diff alone,
             and to keep reasoning about untested inputs even when tests pass
eval/      run_eval.py: runs both reviewers over the same mutant set in
             parallel, computes precision/recall/F1/cost/latency
           capture_trajectory.py: dumps a full tool-call-by-tool-call
             transcript for one case, for both reviewers
results/   RESULTS.md + eval_results.json — the recorded run this README reports
docs/trajectories/  three representative full trajectories (see below)
```

**Design choices and why (Agent Solution & Engineering):**
- **Tools**: the agent gets exactly two — `Read` (see the full file, not
  just the diff) and `Bash` scoped to `python3 -m pytest*` (nothing else —
  it cannot edit files, browse the network, or run arbitrary shell). This
  is a purposeful, minimal grant: enough to ground its judgment in real
  execution, not enough to do anything consequential.
- **Verification**: the prompt explicitly requires the agent to run the
  real test suite and quote its actual output before answering, and to
  keep reasoning about untested inputs even when the suite passes — this
  is the concrete instance of "verification can catch errors before they
  reach the user" from the brief: it forces execution-grounded evidence
  instead of a plausible-sounding guess.
- **Structured output**: both reviewers answer through a strict JSON
  schema (`verdict`, `confidence`, `evidence`, `reasoning`) via
  `claude -p --json-schema`, so grading is exact string comparison, not
  fuzzy text parsing.
- **Fair baseline**: same model, same question, same output schema — the
  only difference is tools and the verification instruction. This isolates
  what those two choices are worth.

## Reproduction guide

From a clean checkout, on a machine with the `claude` CLI already
authenticated (this uses your existing Claude Code login/plan, not a
separate API key):

```bash
pip3 install pytest                       # only external dependency

# 1. Sanity-check the corpus itself (should be 47 passed)
cd corpus && python3 -m pytest -q && cd ..

# 2. Regenerate the mutant set deterministically (no API calls, ~1s)
python3 mutator/generate_mutants.py
#   -> mutants/<module>/<index>.json, mutants/summary.json

# 3. Run the full evaluation (calls `claude -p` ~44 times; ~4 min wall
#    clock with 4 parallel workers; ~$2.30 of usage on claude-sonnet-5)
python3 eval/run_eval.py --killed-per-module 3 --survived-per-module 3 --workers 4
#   -> results/eval_results.json, results/RESULTS.md

# 4. (optional) re-render one full trajectory
python3 eval/capture_trajectory.py token_bucket 13 my_case
#   -> docs/trajectories/my_case_baseline.md, my_case_agent.md
```

Versions used for the recorded results: `claude` CLI 2.1.251, model
`claude-sonnet-5`, Python 3.11.15, pytest 9.1.1. Mutation generation is
fully deterministic (same source → same numbered mutation list every
time); the reviewer calls are not bit-for-bit deterministic (LLM sampling),
so a re-run's exact confidence/wording will differ, but the aggregate
precision/recall/accuracy have been stable across repeated runs in
testing.

## Primary metric and results

**Primary metric:** bug-detection accuracy against test-execution ground
truth — a "killed" mutant (the module's own test suite fails) is ground
truth `bug`; a "survived" mutant (full suite still passes) is ground truth
`no_bug`. 22 cases: 12 killed + 10 survived (3 of each per module, except
`signup_validator`, which only produced 1 survived mutant out of 30 —
its test suite is unusually thorough).

| Metric | Baseline (1 prompt, no tools) | Agent (tools + verification) |
|---|---|---|
| Accuracy | 68.2% | **86.4%** |
| Precision | 69.2% | 80.0% |
| Recall | 75.0% | **100%** |
| F1 | 0.72 | **0.889** |
| False negatives (missed a real bug) | 3 | **0** |
| False positives (flagged a non-bug) | 4 | 3 |
| Cost per case | $0.027 | $0.077 |
| Latency per case | 10.1s | 22.6s |

The agent costs ~2.9x more and takes ~2.2x longer per review — the honest
trade this buys: it never misses a real bug in this set, where the
baseline missed 3 (see below), and it corrects a specific, repeatable
baseline failure mode: confidently declaring a bug from a diff-only
hypothetical that doesn't actually happen given how the function is called
(see the "challenging case" below).

Full per-case results, including every prompt and verdict: `results/eval_results.json`.

### One challenging case, explained

`interval_merge` mutant #6 changes `if next_start - end > 1` to
`if next_start - end >= 1` inside `gaps()`. The baseline reviewer answers
**"bug", confidence 0.97**, with a specific counterexample: "merged
intervals `(1,5)` and `(6,10)` would wrongly produce a gap `(6,5)`". That
counterexample is wrong: `gaps()` only ever receives the output of
`merge_intervals()`, which merges any two intervals with
`next_start <= end + 1` — so `(1,5)` and `(6,10)` could never both appear
in `merged` in the first place (they'd already be merged into `(1,10)`).
The agent reviewer reads the full file, runs the real suite (10 passed),
and — instead of stopping there — traces `merge_intervals()`'s own
invariant to show the changed branch is unreachable, correctly answering
**"no_bug", confidence 0.9**. Full transcripts of both:
`docs/trajectories/equivalent_mutant_{baseline,agent}.md`.

This is the clearest evidence in the whole run for *why* tool access plus
verification matters here: the baseline's mistake isn't a lack of
reasoning ability, it's reasoning about a hypothetical input instead of
checking whether that input is actually reachable — exactly the gap that
execution (or, short of that, reading the calling code) closes.

## Improvement changelog

| Stage | What was tried and why | Evidence | Decision |
|---|---|---|---|
| Iteration 0 (removed) | First attempt used a parallel multi-agent workflow to author the synthetic corpus in bulk. It hit API limits mid-run in a container that then got reclaimed before anything was committed — all of that work was lost. | 8 of 12 planned modules were generated but 0 were ever pushed; the next session started from an empty corpus. | **Removed.** Switched to writing the 4 corpus modules directly, single-session, with a commit after every file — no generation work is allowed to exist only in an uncommitted, ephemeral container again. |
| Baseline | One direct prompt: the unified diff only, no tools, no test execution, forced through the same JSON-schema verdict as everything else. This is the brief's requested "simple baseline". | 68.2% accuracy, 75% recall, **missed all 3 real bugs in `signup_validator`** entirely (an off-by-one in a length constant reads as plausible from the diff text alone). | Kept as the fixed comparison point for every later change. |
| Iteration 1 | Gave the reviewer two tools (`Read`, `Bash` scoped to pytest-only) plus an explicit instruction to run the real suite and quote its output — not just reason from the diff — and to keep reasoning about untested inputs even when the suite passes. | Accuracy 68.2% → 86.4%, recall 75% → **100%** (0 missed bugs), at ~2.9x cost and ~2.2x latency per case. | **Kept.** This is the final "agent" configuration. |
| Debugging note (not a design change, but shaped the tooling) | Every tool-scoped `claude -p` call was silently swallowing the prompt itself and failing with "Input must be provided via stdin or as a prompt argument." Root cause: `--allowedTools`/`--disallowedTools` are variadic CLI options that greedily consume the *next* argv token too when passed as two separate args — including the prompt. | Before the fix: 100% of tool-restricted invocations failed. After joining as `--flag=value` in one token: 0 failures across the full 44-call eval run. | Fixed in `reviewer/common.py`; documented here because it's exactly the kind of infra failure mode that looks like a model problem until you check the actual argv. |
| Post-hoc audit | Manually inspected all 3 of the agent's "false positives" against ground truth. Found: `token_bucket` mutant #13 (`elapsed = now - last_refill` → `now + last_refill`) is a genuine rate-limit-bypass bug that "survives" only because every test's `FakeClock` starts at `0`, so addition and subtraction coincide; the agent's own trajectory correctly diagnoses this and calls it a real bug. The other two false positives follow the same pattern. | See "Hot take" below — this changes the interpretation of the precision number, not the code. | **Not corrected in the reported metric** (keeps the ground truth mechanical and reproducible) but documented as the main caveat — see `docs/trajectories/masked_real_bug_agent.md`. |

## Main failure mode and hot take

**The measurement itself has a blind spot that mirrors the problem it's
trying to study.** "Survived" (all tests still pass) is being used as a
stand-in for "not a bug" — but a mutant can survive for two very different
reasons: it's a true equivalent mutant (the changed branch is provably
unreachable, like the `interval_merge` case above), or it's a **real bug
the test suite happens not to cover** (like `token_bucket` #13, an actual
rate-limit bypass masked because every test's fake clock starts at
exactly zero, so `now + 0` and `now - 0` are indistinguishable). Naive
kill/survive mutation scoring conflates these two into one "no_bug" label.
Manual audit of every one of the agent's 3 "false positives" in this run
found the second kind, not the first — meaning the agent's *true*
precision on this set is very likely higher than 80%, and the honest
takeaway is that its "false positives" here are really a review agent
finding gaps in the corpus's own tests.

**The practical lesson for building reliable agents:** don't let "the test
suite still passes" be the last word on a change — for either a mutation
benchmark or a real PR review pipeline. A reviewer (human or agent) that
only checks "did anything break" inherits every blind spot the existing
tests already have. The one thing that actually caught these cases here
was an agent explicitly instructed to keep reasoning about untested inputs
*after* a passing test run, instead of treating green tests as proof. If I
extended this project, the next iteration would be exactly that: use the
reviewer's own flagged "survived but still suspicious" cases to
auto-suggest the missing test case (e.g. "add a test that calls `_refill`
twice with an intervening `clock.advance`"), closing the loop between
review and test coverage instead of treating them as separate concerns.

## Agent trajectories

Three full, representative tool-call-by-tool-call transcripts (prompt →
tool calls → tool results → final structured verdict) for both reviewers
on the same case:

- `docs/trajectories/equivalent_mutant_{baseline,agent}.md` — the
  challenging case above (baseline false positive from an unreachable
  hypothetical; agent correctly clears it by tracing the invariant).
- `docs/trajectories/boundary_off_by_one_{baseline,agent}.md` — a real bug
  the baseline misses entirely (`no_bug`, wrong) that the agent catches by
  actually running the suite.
- `docs/trajectories/masked_real_bug_{baseline,agent}.md` — the
  `token_bucket` rate-limit-bypass case discussed in the hot take; the
  agent's trajectory contains its full derivation of why the bug is real
  despite the passing test suite.

## Solution video

[https://youtu.be/UVs6c3nyBLw](https://youtu.be/UVs6c3nyBLw) (unlisted, ~3 min) — problem framing, the baseline vs. agent run, the boundary-check case, and the results/changelog. Everything it shows is also runnable directly via the reproduction guide above and the three trajectories linked above.

## Ground rules checklist

- All corpus code and tests are synthetic, written for this project — no
  real user, employer, or third-party data or code anywhere in the repo.
- No API keys are stored or required; the reviewers call the already-
  authenticated local `claude` CLI.
- The agent reviewer's only tools are `Read` and `Bash` scoped to
  `python3 -m pytest*` inside a disposable temp directory it cannot escape
  — it cannot write files, reach the network, or affect anything outside
  that sandbox. Mutation and test execution both happen in isolated temp
  copies, never against the tracked `corpus/` files.
- This is a decision-support signal, not an auto-merge system: nothing
  here takes a consequential action (merging, deploying, editing a real
  repo) on its own; a real deployment of this idea would still gate any
  merge decision on human sign-off.
