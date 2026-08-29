import pytest

from token_bucket import MultiKeyRateLimiter, TokenBucket


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_starts_full():
    clock = FakeClock()
    bucket = TokenBucket(capacity=10, rate=1, clock=clock)
    assert bucket.available_tokens() == 10


def test_acquire_consumes_tokens():
    clock = FakeClock()
    bucket = TokenBucket(capacity=10, rate=1, clock=clock)
    assert bucket.try_acquire(4) is True
    assert bucket.available_tokens() == 6


def test_acquire_fails_when_insufficient():
    clock = FakeClock()
    bucket = TokenBucket(capacity=5, rate=1, clock=clock)
    assert bucket.try_acquire(5) is True
    assert bucket.try_acquire(1) is False
    assert bucket.available_tokens() == 0


def test_refill_over_time():
    clock = FakeClock()
    bucket = TokenBucket(capacity=10, rate=2, clock=clock)
    bucket.try_acquire(10)
    clock.advance(3)  # +6 tokens
    assert bucket.available_tokens() == 6


def test_refill_caps_at_capacity():
    clock = FakeClock()
    bucket = TokenBucket(capacity=10, rate=2, clock=clock)
    bucket.try_acquire(2)
    clock.advance(100)
    assert bucket.available_tokens() == 10


def test_time_until_available():
    clock = FakeClock()
    bucket = TokenBucket(capacity=10, rate=2, clock=clock)
    bucket.try_acquire(10)
    assert bucket.time_until_available(4) == 2.0
    assert bucket.time_until_available(0.0001) > 0


def test_time_until_available_when_already_available():
    clock = FakeClock()
    bucket = TokenBucket(capacity=10, rate=2, clock=clock)
    assert bucket.time_until_available(3) == 0.0


def test_zero_rate_never_refills():
    clock = FakeClock()
    bucket = TokenBucket(capacity=5, rate=0, clock=clock)
    bucket.try_acquire(5)
    clock.advance(1000)
    assert bucket.available_tokens() == 0
    assert bucket.time_until_available(1) == float("inf")


def test_invalid_capacity_rejected():
    with pytest.raises(ValueError):
        TokenBucket(capacity=0, rate=1)


def test_invalid_cost_rejected():
    bucket = TokenBucket(capacity=5, rate=1)
    with pytest.raises(ValueError):
        bucket.try_acquire(0)


def test_multi_key_limiter_isolates_keys():
    clock = FakeClock()
    limiter = MultiKeyRateLimiter(capacity=2, rate=1, clock=clock)
    assert limiter.try_acquire("user-a", 2) is True
    assert limiter.try_acquire("user-a", 1) is False
    # user-b has its own independent bucket
    assert limiter.try_acquire("user-b", 2) is True
    assert set(limiter.known_keys()) == {"user-a", "user-b"}
