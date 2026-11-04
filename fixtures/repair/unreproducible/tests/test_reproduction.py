import pytest

from app import average


def test_average_rejects_empty_input():
    with pytest.raises(ValueError, match='empty'):
        average([])
