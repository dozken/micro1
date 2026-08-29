"""Token-bucket rate limiter."""
from __future__ import annotations

from typing import Callable, Dict


class TokenBucket:
    """Classic token-bucket limiter: holds up to `capacity` tokens, refills
    at `rate` tokens/second, and a request of `cost` tokens is allowed only
    if enough tokens are currently available."""

    def __init__(self, capacity: float, rate: float, clock: Callable[[], float] = None):
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if rate < 0:
            raise ValueError("rate must be >= 0")
        self.capacity = capacity
        self.rate = rate
        self._clock = clock or __import__("time").monotonic
        self._tokens = capacity
        self._last_refill = self._clock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self._last_refill = now

    def try_acquire(self, cost: float = 1.0) -> bool:
        if cost <= 0:
            raise ValueError("cost must be > 0")
        self._refill()
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    def available_tokens(self) -> float:
        self._refill()
        return self._tokens

    def time_until_available(self, cost: float = 1.0) -> float:
        """Seconds until `cost` tokens will be available (0 if available now)."""
        self._refill()
        deficit = cost - self._tokens
        if deficit <= 0:
            return 0.0
        if self.rate == 0:
            return float("inf")
        return deficit / self.rate


class MultiKeyRateLimiter:
    """Per-key token buckets sharing the same capacity/rate, created lazily."""

    def __init__(self, capacity: float, rate: float, clock: Callable[[], float] = None):
        self.capacity = capacity
        self.rate = rate
        self._clock = clock
        self._buckets: Dict[str, TokenBucket] = {}

    def _bucket_for(self, key: str) -> TokenBucket:
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(self.capacity, self.rate, clock=self._clock)
            self._buckets[key] = bucket
        return bucket

    def try_acquire(self, key: str, cost: float = 1.0) -> bool:
        return self._bucket_for(key).try_acquire(cost)

    def known_keys(self):
        return list(self._buckets.keys())
