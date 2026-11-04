import pytest

from app import parse_port


def test_none_is_rejected_as_invalid_argument():
    with pytest.raises(ValueError):
        parse_port(None)
