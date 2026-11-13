from app import checksum

def test_checksum():
    assert checksum([2, 3]) == 5
