import pytest
from app import parse_count

def test_case():
    with pytest.raises(ValueError):
        parse_count("unknown")
