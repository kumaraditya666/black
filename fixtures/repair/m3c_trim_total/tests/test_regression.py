from app import total

def test_regular_values():
    assert total(['1', '2']) == 3

def test_empty_collection():
    assert total([]) == 0

def test_whitespace_value():
    assert total(['  ', '7']) == 7
