import pytest

from lru_ttl_cache import LRUTTLCache


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_basic_put_get():
    cache = LRUTTLCache(capacity=2)
    cache.put("a", 1)
    assert cache.get("a") == 1
    assert cache.get("missing") is None
    assert cache.get("missing", "default") == "default"


def test_capacity_zero_stores_nothing():
    cache = LRUTTLCache(capacity=0)
    cache.put("a", 1)
    assert len(cache) == 0
    assert cache.get("a") is None


def test_eviction_order_is_least_recently_used():
    cache = LRUTTLCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)  # evicts "a", the least recently used
    assert "a" not in cache
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert len(cache) == 2


def test_get_refreshes_recency():
    cache = LRUTTLCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")  # "a" is now most-recently used
    cache.put("c", 3)  # should evict "b", not "a"
    assert "b" not in cache
    assert cache.get("a") == 1
    assert cache.get("c") == 3


def test_overwrite_existing_key_updates_value_and_recency():
    cache = LRUTTLCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 99)  # "a" moves to most-recently-used, value updates
    cache.put("c", 3)  # should evict "b"
    assert "b" not in cache
    assert cache.get("a") == 99
    assert cache.get("c") == 3


def test_ttl_expiry():
    clock = FakeClock()
    cache = LRUTTLCache(capacity=2, clock=clock)
    cache.put("a", 1, ttl=10)
    clock.advance(5)
    assert cache.get("a") == 1
    clock.advance(6)
    assert cache.get("a") is None
    assert "a" not in cache


def test_ttl_boundary_expires_at_exact_instant():
    clock = FakeClock()
    cache = LRUTTLCache(capacity=2, clock=clock)
    cache.put("a", 1, ttl=10)
    clock.advance(10)
    assert cache.get("a") is None


def test_no_ttl_never_expires():
    clock = FakeClock()
    cache = LRUTTLCache(capacity=2, clock=clock)
    cache.put("a", 1)
    clock.advance(10_000)
    assert cache.get("a") == 1


def test_purge_expired_counts_and_removes():
    clock = FakeClock()
    cache = LRUTTLCache(capacity=3, clock=clock)
    cache.put("a", 1, ttl=5)
    cache.put("b", 2, ttl=100)
    cache.put("c", 3)
    clock.advance(6)
    removed = cache.purge_expired()
    assert removed == 1
    assert "a" not in cache
    assert "b" in cache
    assert "c" in cache


def test_negative_capacity_rejected():
    with pytest.raises(ValueError):
        LRUTTLCache(capacity=-1)
