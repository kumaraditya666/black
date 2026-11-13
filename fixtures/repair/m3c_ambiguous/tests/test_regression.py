from app import load_number

def test_numeric():
    assert load_number('12') == 12
