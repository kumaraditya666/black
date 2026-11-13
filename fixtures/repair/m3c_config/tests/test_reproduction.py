from app import connect_options

def test_default_retries():
    assert connect_options({}) == {'retries': 3, 'timeout': 5}
