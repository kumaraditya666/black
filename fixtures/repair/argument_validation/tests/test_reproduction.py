import pytest

from app import parse_port


def test_port_above_range_is_rejected():
    with pytest.raises(ValueError):
        parse_port('70000')
