from app import last_or_none

def test_nonempty():
    assert last_or_none([7]) == 7
