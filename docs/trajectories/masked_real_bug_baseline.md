# Trajectory: token_bucket mutant #13 (arithmetic_operator_swap:Sub->Add @ line 25) — BASELINE

## Prompt given to the agent

```
You are reviewing a code change to a small Python utility module.
Below is the unified diff of the change. You do NOT have access to the repository,
you cannot run code, and you cannot read any other file. Judge only from the diff text.

Module: token_bucket.py

```diff
--- a/token_bucket.py
+++ b/token_bucket.py
@@ -20,7 +20,7 @@
 
     def _refill(self) -> None:
         now = self._clock()
-        elapsed = now - self._last_refill
+        elapsed = now + self._last_refill
         if elapsed > 0:
             self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
             self._last_refill = now

```

Does this change introduce a behavioral bug? Give your verdict, confidence,
the concrete evidence for it (quote the specific line(s) and explain the
concrete input that would misbehave), and your reasoning.
```

## Turn-by-turn trajectory

**Assistant (final/interim text):**

**Verdict: Yes, this introduces a behavioral bug. Confidence: high.**

**Evidence:**
```python
elapsed = now + self._last_refill
```
This replaces the correct `elapsed = now - self._last_refill` with addition. `elapsed` should be the time delta since the last refill, but `now + self._last_refill` computes a sum of two timestamps, which is not a duration at all.

**Concrete misbehavior:**

Assume `self._clock()` returns a monotonically increasing timestamp (e.g., `time.monotonic()`), and `self._last_refill` was initialized to, say, `1000.0`. On the next call, `now = 1000.5` (half a second later, `_last_refill` unchanged since this is the first refill check).

- Correct: `elapsed = 1000.5 - 1000.0 = 0.5` → tokens increase by `0.5 * rate`.
- Buggy: `elapsed = 1000.5 + 1000.0 = 2000.5` → tokens increase by `2000.5 * rate`, i.e. ~4001x too much (and then clamped by `min(self.capacity, ...)`, so the bucket is instantly filled to full capacity regardless of how little time actually passed).

Effect: the token bucket refills to full capacity almost immediately, since `elapsed` will be some large positive number (sum of two timestamps) rather than a small delta, as long as both `now` and `_last_refill` are positive (true for any wall-clock or monotonic clock). This defeats rate limiting entirely — callers get essentially unlimited tokens after the first refill call, since `_tokens` gets clamped to `capacity` almost every time `_refill` runs.

Additionally, if timestamps could ever be such that `now + self._last_refill <= 0` (unlikely in practice but possible with negative/mocked clocks), the `if elapsed > 0` guard would skip refilling, causing the bucket to never refill — a starvation bug in that edge case.

The core, always-triggering issue is the capacity-clamping runaway refill described above: this is a clear correctness regression, not a stylistic nit.

## Final structured output

```json
**Verdict: Yes, this introduces a behavioral bug. Confidence: high.**

**Evidence:**
```python
elapsed = now + self._last_refill
```
This replaces the correct `elapsed = now - self._last_refill` with addition. `elapsed` should be the time delta since the last refill, but `now + self._last_refill` computes a sum of two timestamps, which is not a duration at all.

**Concrete misbehavior:**

Assume `self._clock()` returns a monotonically increasing timestamp (e.g., `time.monotonic()`), and `self._last_refill` was initialized to, say, `1000.0`. On the next call, `now = 1000.5` (half a second later, `_last_refill` unchanged since this is the first refill check).

- Correct: `elapsed = 1000.5 - 1000.0 = 0.5` → tokens increase by `0.5 * rate`.
- Buggy: `elapsed = 1000.5 + 1000.0 = 2000.5` → tokens increase by `2000.5 * rate`, i.e. ~4001x too much (and then clamped by `min(self.capacity, ...)`, so the bucket is instantly filled to full capacity regardless of how little time actually passed).

Effect: the token bucket refills to full capacity almost immediately, since `elapsed` will be some large positive number (sum of two timestamps) rather than a small delta, as long as both `now` and `_last_refill` are positive (true for any wall-clock or monotonic clock). This defeats rate limiting entirely — callers get essentially unlimited tokens after the first refill call, since `_tokens` gets clamped to `capacity` almost every time `_refill` runs.

Additionally, if timestamps could ever be such that `now + self._last_refill <= 0` (unlikely in practice but possible with negative/mocked clocks), the `if elapsed > 0` guard would skip refilling, causing the bucket to never refill — a starvation bug in that edge case.

The core, always-triggering issue is the capacity-clamping runaway refill described above: this is a clear correctness regression, not a stylistic nit.
```

Cost: $0.0234 | Turns: 1 | Duration: 9398ms
