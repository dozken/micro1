"""A small LRU cache with optional per-entry time-to-live (TTL)."""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable, Optional


class LRUTTLCache:
    """Fixed-capacity cache, evicting least-recently-used entries once full.
    Entries may carry a TTL (seconds); expired entries are treated as
    missing and are purged lazily on access."""

    def __init__(self, capacity: int, clock: Callable[[], float] = None):
        if capacity < 0:
            raise ValueError("capacity must be >= 0")
        self.capacity = capacity
        self._clock = clock or __import__("time").monotonic
        self._store: "OrderedDict[Any, tuple[Any, Optional[float]]]" = OrderedDict()

    def _is_expired(self, expires_at: Optional[float]) -> bool:
        return expires_at is not None and self._clock() >= expires_at

    def put(self, key: Any, value: Any, ttl: Optional[float] = None) -> None:
        if self.capacity == 0:
            return
        expires_at = None if ttl is None else self._clock() + ttl
        if key in self._store:
            del self._store[key]
        elif len(self._store) >= self.capacity:
            self._store.popitem(last=False)
        self._store[key] = (value, expires_at)

    def get(self, key: Any, default: Any = None) -> Any:
        if key not in self._store:
            return default
        value, expires_at = self._store[key]
        if self._is_expired(expires_at):
            del self._store[key]
            return default
        self._store.move_to_end(key)
        return value

    def __contains__(self, key: Any) -> bool:
        return self.get(key, _MISSING) is not _MISSING

    def purge_expired(self) -> int:
        """Remove all currently-expired entries; return how many were
        removed."""
        expired_keys = [
            key for key, (_, expires_at) in self._store.items()
            if self._is_expired(expires_at)
        ]
        for key in expired_keys:
            del self._store[key]
        return len(expired_keys)

    def __len__(self) -> int:
        return len(self._store)

    def keys(self):
        return list(self._store.keys())


_MISSING = object()
