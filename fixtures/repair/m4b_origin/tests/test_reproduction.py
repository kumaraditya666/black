import pytest
from app import parse_count

def test_bad_input():
    with pytest.raises(ValueError):
        parse_count("unknown")
