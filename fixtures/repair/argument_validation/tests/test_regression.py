import pytest

from app import parse_port


def test_valid_port_is_parsed():
    assert parse_port('8080') == 8080


def test_non_numeric_value_is_rejected():
    with pytest.raises(ValueError):
        parse_port('http')


def test_zero_is_rejected():
    with pytest.raises(ValueError):
        parse_port('0')
