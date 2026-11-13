from app import take

def test_default_limit():
    assert take([1, 2], {}) == [1, 2]
