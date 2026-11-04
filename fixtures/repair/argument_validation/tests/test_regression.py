import pytest

from app import parse_port


def test_numeric_string_port_is_parsed():
    assert parse_port('8080') == 8080


def test_invalid_text_is_rejected():
    with pytest.raises(ValueError):
        parse_port('http')


def test_none_is_rejected():
    with pytest.raises(ValueError):
        parse_port(None)
