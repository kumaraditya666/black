from app import require_full_window

def test_multiple_windows():
    assert require_full_window([1, 2, 3, 4], 2) == [3, 5, 7]

def test_no_full_window():
    assert require_full_window([1], 2) == []
