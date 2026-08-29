# Submission checklist — what's left to do

Deadline: **Aug 31, 2026** (HackerEarth, micro1 Frontier Engineering Challenge).

Everything in the repo is finished and merged to `main`. The remaining items
below need a human (account access / screen recording) and cannot be done by
the agent.

## 1. Solution video — done

Recorded, narrated (Kokoro TTS, local re-synth of the original narration),
uploaded to YouTube unlisted: https://youtu.be/UVs6c3nyBLw. Linked from
`README.md`.

## 2. Submit the HackerEarth form

- Repo link: `https://github.com/dozken/micro1` (default branch `main` has everything).
- Video URL: https://youtu.be/UVs6c3nyBLw
- The write-up fields can be filled from `README.md` — the sections map 1:1
  to the judging rubric (problem & user value, agent solution & engineering,
  measured improvement, reproducibility, hot take).

## 3. Make the repo accessible to judges — worth 15 points — done

Repo is public: https://github.com/dozken/micro1

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
