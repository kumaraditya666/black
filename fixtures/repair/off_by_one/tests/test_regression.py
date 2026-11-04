from app import last_n


def test_zero_count_returns_empty():
    assert last_n([1, 2], 0) == []


def test_count_larger_than_list_returns_all():
    assert last_n([1, 2], 5) == [1, 2]


def test_whole_list_is_returned():
    assert last_n([1, 2, 3], 3) == [1, 2, 3]
