from app import find_index


def test_first_item_is_found():
    assert find_index([1, 2, 3], 1) == 0


def test_last_item_is_found():
    assert find_index([1, 2, 3], 3) == 2


def test_empty_list_has_no_match():
    assert find_index([], 1) == -1
