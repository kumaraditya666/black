from app import request_timeout


def test_missing_timeout_uses_default():
    assert request_timeout({}) == 30
