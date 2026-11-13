from app import select

def test_default():
    assert select([1, 2], {}) == [1, 2]
