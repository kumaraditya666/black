from app import parse_count

def test_number():
    assert parse_count("4") == 4
