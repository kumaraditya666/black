from app import first_or_none

def test_nonempty():
    assert first_or_none([4]) == 4
