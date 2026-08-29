# Submission checklist — what's left to do

Deadline: **Aug 31, 2026** (HackerEarth, micro1 Frontier Engineering Challenge).

Everything in the repo is finished and merged to `main`. The remaining items
below need a human (account access / screen recording) and cannot be done by
the agent.

## 1. Record the solution video (≤ 5 minutes) — required deliverable

Suggested flow, timed to fit:

| Time | Segment | What to show |
|---|---|---|
| 0:00–0:30 | Problem | Who has it (teams merging AI-authored PRs), the bottleneck (silent regressions that pass existing tests). One sentence on the baseline: same model, diff only, no tools. |
| 0:30–2:30 | One realistic execution | Either run live: `python3 eval/run_eval.py --killed-per-module 1 --survived-per-module 1 --workers 4` (~90s), or walk through `results/RESULTS.md` if recording time is tight. |
| 2:30–4:00 | The challenging case | Open `docs/trajectories/equivalent_mutant_baseline.md` vs `..._agent.md` side by side: baseline confidently wrong (0.97 "bug" from an unreachable hypothetical), agent traces the invariant and clears it. |
| 4:00–5:00 | Comparison + changelog | Results table (86.4%/100% recall vs 68.2%/75%). Changelog highlights: the change that contributed most (tools + verification instruction, Iteration 1) and the removed experiment (Iteration 0, the lost multi-agent corpus run). |

## 2. Submit the HackerEarth form

- Repo link: `https://github.com/dozken/micro1` (default branch `main` has everything).
- Attach/link the video from step 1.
- The write-up fields can be filled from `README.md` — the sections map 1:1
  to the judging rubric (problem & user value, agent solution & engineering,
  measured improvement, reproducibility, hot take).

## 3. Make the repo accessible to judges — worth 15 points

The repo is currently **private**. Ground rule #10 requires judges be able
to run the project. Either:

- make the repo public (Settings → General → Danger Zone → Change visibility), or
- grant access however the HackerEarth submission instructions specify.

## Optional, if time allows

- Re-run the eval once more before recording (`python3 eval/run_eval.py ...`)
  so the video shows fresh output; aggregate numbers have been stable across
  runs but exact wording/confidence will differ.
- Skim `results/eval_results.json` for a second interesting case to mention.

## Pre-flight sanity check (2 minutes, from a clean clone)

```bash
git clone https://github.com/dozken/micro1 && cd micro1
pip3 install pytest
cd corpus && python3 -m pytest -q && cd ..   # expect: 47 passed
python3 mutator/generate_mutants.py           # expect: 133 mutants, ~1s, no API calls
```

If both commands behave as expected, the reproducibility story holds from a
clean environment.
