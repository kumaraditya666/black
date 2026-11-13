from app import require_entries

def test_entries():
    assert require_entries(['a']) == 1
