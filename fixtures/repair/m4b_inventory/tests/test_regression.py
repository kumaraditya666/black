from app import select

def test_explicit():
    assert select([1, 2], {"limit": 1}) == [1]
