import pytest

from app import average


def test_average_of_values():
    assert average([2, 4]) == 3.0


def test_average_of_single_value():
    assert average([5]) == 5.0


def test_average_still_rejects_empty():
    with pytest.raises(ValueError):
        average([])
