from app import require_full_window

def test_exact_window():
    assert require_full_window([1, 2, 3], 3) == [6]
