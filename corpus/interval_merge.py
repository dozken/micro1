"""Merge and query overlapping integer intervals."""
from __future__ import annotations

from typing import List, Tuple

Interval = Tuple[int, int]


def merge_intervals(intervals: List[Interval]) -> List[Interval]:
    """Merge overlapping/touching [start, end] intervals (inclusive) into a
    minimal sorted list. Touching intervals like (1, 3) and (3, 5) merge into
    (1, 5)."""
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda iv: iv[0])
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def total_covered(intervals: List[Interval]) -> int:
    """Number of distinct integers covered by the union of intervals."""
    return sum(end - start + 1 for start, end in merge_intervals(intervals))


def contains_point(intervals: List[Interval], point: int) -> bool:
    """True if `point` falls within any merged interval, inclusive bounds."""
    for start, end in merge_intervals(intervals):
        if start <= point <= end:
            return True
    return False


def gaps(intervals: List[Interval]) -> List[Interval]:
    """Return the gaps strictly between merged intervals (not before the
    first or after the last)."""
    merged = merge_intervals(intervals)
    result = []
    for (_, end), (next_start, _) in zip(merged, merged[1:]):
        if next_start - end > 1:
            result.append((end + 1, next_start - 1))
    return result


def insert_interval(intervals: List[Interval], new: Interval) -> List[Interval]:
    """Insert `new` into an already-merged, sorted interval list and
    re-merge."""
    return merge_intervals(list(intervals) + [new])
