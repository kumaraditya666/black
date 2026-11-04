from app import request_timeout


def test_explicit_timeout_is_used():
    assert request_timeout({'timeout': 5}) == 5


def test_zero_timeout_is_preserved():
    assert request_timeout({'timeout': 0}) == 0
