from app import checksum

def test_empty():
    assert checksum([]) == 0
