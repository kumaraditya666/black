from app import first_or_none

def test_empty_list():
    assert first_or_none([]) is None
