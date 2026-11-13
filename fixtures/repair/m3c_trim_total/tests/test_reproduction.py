from app import total

def test_blank_values_are_ignored():
    assert total([' 12 ', '', '1,000']) == 1012
