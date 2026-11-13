from app import take

def test_explicit_limit():
    assert take([1, 2], {'max_items': 1}) == [1]
