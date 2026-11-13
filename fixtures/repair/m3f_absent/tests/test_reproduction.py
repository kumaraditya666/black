from app import last_or_none

def test_empty():
    assert last_or_none([]) is None
