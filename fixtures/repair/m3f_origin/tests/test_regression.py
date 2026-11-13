from app import read_score

def test_numeric_score():
    assert read_score('4') == 4
