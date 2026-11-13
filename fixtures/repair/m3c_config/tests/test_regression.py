from app import connect_options

def test_explicit_zero_retries():
    assert connect_options({'retries': 0})['retries'] == 0

def test_string_and_timeout():
    assert connect_options({'retries': '2', 'timeout': 0}) == {'retries': 2, 'timeout': 0}
