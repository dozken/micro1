from interval_merge import (
    contains_point,
    gaps,
    insert_interval,
    merge_intervals,
    total_covered,
)


def test_merge_empty():
    assert merge_intervals([]) == []


def test_merge_no_overlap():
    assert merge_intervals([(1, 2), (4, 5)]) == [(1, 2), (4, 5)]


def test_merge_overlap():
    assert merge_intervals([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


def test_merge_touching():
    assert merge_intervals([(1, 3), (3, 5)]) == [(1, 5)]
    assert merge_intervals([(1, 3), (4, 5)]) == [(1, 5)]


def test_merge_unsorted_input():
    assert merge_intervals([(5, 6), (1, 2)]) == [(1, 2), (5, 6)]


def test_merge_nested():
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]


def test_total_covered():
    assert total_covered([(1, 3), (2, 6)]) == 6
    assert total_covered([]) == 0
    assert total_covered([(5, 5)]) == 1


def test_contains_point():
    ivs = [(1, 3), (10, 12)]
    assert contains_point(ivs, 2)
    assert contains_point(ivs, 1)
    assert contains_point(ivs, 3)
    assert not contains_point(ivs, 4)
    assert not contains_point(ivs, 9)
    assert contains_point(ivs, 10)


def test_gaps():
    assert gaps([(1, 3), (6, 8), (10, 10)]) == [(4, 5), (9, 9)]
    assert gaps([(1, 3)]) == []
    assert gaps([(1, 3), (4, 5)]) == []


def test_insert_interval():
    # (2, 5) bridges (1, 3) and (6, 9): 5 touches 6 (5 + 1 == 6), so they merge into one.
    assert insert_interval([(1, 3), (6, 9)], (2, 5)) == [(1, 9)]
    assert insert_interval([(1, 2), (5, 7)], (9, 10)) == [(1, 2), (5, 7), (9, 10)]
