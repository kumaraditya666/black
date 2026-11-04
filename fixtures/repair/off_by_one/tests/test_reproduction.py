from app import find_index


def test_absent_target_returns_minus_one():
    assert find_index([1, 2, 3], 4) == -1
