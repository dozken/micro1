# Trajectory: token_bucket mutant #13 (arithmetic_operator_swap:Sub->Add @ line 25) — AGENT

## Prompt given to the agent

```
You are reviewing a code change to a small Python utility module in this
directory. Here is the unified diff of the change:

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

You have two tools available: Read (to read any file in this directory,
including the full module and its existing test file) and Bash, restricted
to running `python3 -m pytest`.

Do not just reason from the diff. Before giving your final verdict:
1. Read the full mutated module (token_bucket.py) to understand the change in context.
2. Run the existing test suite (`python3 -m pytest -q test_token_bucket.py`) and
   quote the actual pass/fail output — do not guess or paraphrase what you
   expect it to say.
3. If all tests pass, that does not automatically mean there is no bug —
   the test suite may simply not cover the changed behavior. Reason about
   whether the change could still misbehave on inputs the tests don't
   exercise, and say so explicitly.

Give your verdict, confidence, the concrete evidence (quote real pytest
output and/or a specific input/output pair you reasoned through), and your
reasoning.
```

## Turn-by-turn trajectory

**Tool call:** `Read`  input: `{"file_path": "/tmp/traj_agent_npn3fsti/token_bucket.py"}`

**Tool result:**
```
1	"""Token-bucket rate limiter."""
2	from __future__ import annotations
3	from typing import Callable, Dict
4	
5	class TokenBucket:
6	    """Classic token-bucket limiter: holds up to `capacity` tokens, refills
7	    at `rate` tokens/second, and a request of `cost` tokens is allowed only
8	    if enough tokens are currently available."""
9	
10	    def __init__(self, capacity: float, rate: float, clock: Callable[[], float]=None):
11	        if capacity <= 0:
12	            raise ValueError('capacity must be > 0')
13	        if rate < 0:
14	            raise ValueError('rate must be >= 0')
15	        self.capacity = capacity
16	        self.rate = rate
17	        self._clock = clock or __import__('time').monotonic
18	        self._tokens = capacity
19	        self._last_refill = self._clock()
20	
21	    def _refill(self) -> None:
22	        now = self._clock()
23	        elapsed = now + self._last_refill
24	        if elapsed > 0:
25	            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
26	            self._last_refill = now
27	
28	    def try_acquire(self, cost: float=1.0) -> bool:
29	        if cost <= 0:
30	            raise ValueError('cost must be > 0')
31	        self._refill()
32	        if self._tokens >= cost:
33	            self._tokens -= cost
34	            return True
35	        return False
36	
37	    def available_tokens(self) -> float:
38	        self._refill()
39	        return self._tokens
40	
41	    def time_until_available(self, co
...[truncated]
```

**Tool call:** `Bash`  input: `{"command": "python3 -m pytest -q test_token_bucket.py 2>&1"}`

**Tool result:**
```
...........                                                              [100%]
11 passed in 0.02s
```

**Tool call:** `Read`  input: `{"file_path": "/tmp/traj_agent_npn3fsti/test_token_bucket.py"}`

**Tool result:**
```
1	import pytest
2	
3	from token_bucket import MultiKeyRateLimiter, TokenBucket
4	
5	
6	class FakeClock:
7	    def __init__(self, start: float = 0.0):
8	        self.now = start
9	
10	    def __call__(self) -> float:
11	        return self.now
12	
13	    def advance(self, seconds: float) -> None:
14	        self.now += seconds
15	
16	
17	def test_starts_full():
18	    clock = FakeClock()
19	    bucket = TokenBucket(capacity=10, rate=1, clock=clock)
20	    assert bucket.available_tokens() == 10
21	
22	
23	def test_acquire_consumes_tokens():
24	    clock = FakeClock()
25	    bucket = TokenBucket(capacity=10, rate=1, clock=clock)
26	    assert bucket.try_acquire(4) is True
27	    assert bucket.available_tokens() == 6
28	
29	
30	def test_acquire_fails_when_insufficient():
31	    clock = FakeClock()
32	    bucket = TokenBucket(capacity=5, rate=1, clock=clock)
33	    assert bucket.try_acquire(5) is True
34	    assert bucket.try_acquire(1) is False
35	    assert bucket.available_tokens() == 0
36	
37	
38	def test_refill_over_time():
39	    clock = FakeClock()
40	    bucket = TokenBucket(capacity=10, rate=2, clock=clock)
41	    bucket.try_acquire(10)
42	    clock.advance(3)  # +6 tokens
43	    assert bucket.available_tokens() == 6
44	
45	
46	def test_refill_caps_at_capacity():
47	    clock = FakeClock()
48	    bucket = TokenBucket(capacity=10, rate=2, clock=clock)
49	    bucket.try_acquire(2)
50	    clock.advance(100)
51	    assert bucket.available_tokens() == 10
52	
53	
54	def test_ti
...[truncated]
```

**Assistant (final/interim text):**

## Verdict: **Bug — confirmed regression.** High confidence.

### What changed
`token_bucket.py:23`: `elapsed = now - self._last_refill` → `elapsed = now + self._last_refill`. This replaces a time delta with a sum, which is not a valid way to compute elapsed time.

### Test suite result (actual output)
```
$ python3 -m pytest -q test_token_bucket.py
...........                                                              [100%]
11 passed in 0.02s
```
All 11 tests pass — but this is misleading, not exculpatory.

### Why the tests don't catch it
Every test uses `FakeClock(start=0.0)` (test_token_bucket.py:6-14). The bucket's `_last_refill` is initialized to `self._clock()` at construction time, i.e. `0.0`. Crucially, `_last_refill` is only ever updated *inside* the `if elapsed > 0:` block, and every test in the suite calls `clock.advance(...)` at most **once** before checking `available_tokens()`/`time_until_available()`. So at the moment `elapsed` is computed with a non-zero result, `self._last_refill` is still `0.0`, and `now + 0.0 == now - 0.0`. The addition and subtraction are indistinguishable as long as `_last_refill` hasn't yet been updated away from zero — which is true in every single test case. None of them perform a *second* refill-triggering call after time has already advanced once.

### Concrete input where it breaks
Take `TokenBucket(capacity=100, rate=1, clock=FakeClock())`:
1. `t=0`: init, `_last_refill=0`, `tokens=100`.
2. `try_acquire(100)` → tokens=0. `_refill`: `elapsed = 0+0 = 0`, not `>0`, so `_last_refill` stays `0`.
3. `clock.advance(1)` → `t=1`. `available_tokens()`: `elapsed = 1+0 = 1` (still correct by coincidence) → `tokens = 1`, `_last_refill` updates to `1`.
4. `clock.advance(1)` → `t=2`. `available_tokens()`: correct elapsed should be `2-1=1` → `tokens` should become `2`. Buggy code computes `elapsed = 2+1 = 3` → `tokens = 1 + 3*1 = 4`.

So after two real seconds have passed with `rate=1`, the bucket should hold 2 tokens but the buggy code grants 4 — refilling roughly twice as fast as configured, and the error compounds on every subsequent refill call (each one adds `now + last_refill` instead of the true small delta), quickly saturating to `capacity` far faster than the configured rate allows. This is a rate-limit bypass, not just a cosmetic error.

It's also worse in production than in tests: the default clock is `time.monotonic()` (token_bucket.py:17), which does **not** start at 0 — it's typically some arbitrary positive offset (system uptime). So `_last_refill` is non-zero from the very first construction, and the very first `_refill()` call (not just the second) would compute a wildly inflated `elapsed` (`now + last_refill` ≈ `2×now`), instantly maxing the bucket to `capacity` regardless of real elapsed time. The FakeClock-starts-at-zero convention in every test is exactly what hides this from the suite.

**Conclusion:** The diff is a genuine bug that the existing tests fail to catch due to a blind spot in the test fixture (clock always starts at 0, and no test drives two consecutive non-trivial refills). It should be reverted to subtraction.

## Final structured output

```json
## Verdict: **Bug — confirmed regression.** High confidence.

### What changed
`token_bucket.py:23`: `elapsed = now - self._last_refill` → `elapsed = now + self._last_refill`. This replaces a time delta with a sum, which is not a valid way to compute elapsed time.

### Test suite result (actual output)
```
$ python3 -m pytest -q test_token_bucket.py
...........                                                              [100%]
11 passed in 0.02s
```
All 11 tests pass — but this is misleading, not exculpatory.

### Why the tests don't catch it
Every test uses `FakeClock(start=0.0)` (test_token_bucket.py:6-14). The bucket's `_last_refill` is initialized to `self._clock()` at construction time, i.e. `0.0`. Crucially, `_last_refill` is only ever updated *inside* the `if elapsed > 0:` block, and every test in the suite calls `clock.advance(...)` at most **once** before checking `available_tokens()`/`time_until_available()`. So at the moment `elapsed` is computed with a non-zero result, `self._last_refill` is still `0.0`, and `now + 0.0 == now - 0.0`. The addition and subtraction are indistinguishable as long as `_last_refill` hasn't yet been updated away from zero — which is true in every single test case. None of them perform a *second* refill-triggering call after time has already advanced once.

### Concrete input where it breaks
Take `TokenBucket(capacity=100, rate=1, clock=FakeClock())`:
1. `t=0`: init, `_last_refill=0`, `tokens=100`.
2. `try_acquire(100)` → tokens=0. `_refill`: `elapsed = 0+0 = 0`, not `>0`, so `_last_refill` stays `0`.
3. `clock.advance(1)` → `t=1`. `available_tokens()`: `elapsed = 1+0 = 1` (still correct by coincidence) → `tokens = 1`, `_last_refill` updates to `1`.
4. `clock.advance(1)` → `t=2`. `available_tokens()`: correct elapsed should be `2-1=1` → `tokens` should become `2`. Buggy code computes `elapsed = 2+1 = 3` → `tokens = 1 + 3*1 = 4`.

So after two real seconds have passed with `rate=1`, the bucket should hold 2 tokens but the buggy code grants 4 — refilling roughly twice as fast as configured, and the error compounds on every subsequent refill call (each one adds `now + last_refill` instead of the true small delta), quickly saturating to `capacity` far faster than the configured rate allows. This is a rate-limit bypass, not just a cosmetic error.

It's also worse in production than in tests: the default clock is `time.monotonic()` (token_bucket.py:17), which does **not** start at 0 — it's typically some arbitrary positive offset (system uptime). So `_last_refill` is non-zero from the very first construction, and the very first `_refill()` call (not just the second) would compute a wildly inflated `elapsed` (`now + last_refill` ≈ `2×now`), instantly maxing the bucket to `capacity` regardless of real elapsed time. The FakeClock-starts-at-zero convention in every test is exactly what hides this from the suite.

**Conclusion:** The diff is a genuine bug that the existing tests fail to catch due to a blind spot in the test fixture (clock always starts at 0, and no test drives two consecutive non-trivial refills). It should be reverted to subtraction.
```

Cost: $0.1058 | Turns: 4 | Duration: 53904ms
