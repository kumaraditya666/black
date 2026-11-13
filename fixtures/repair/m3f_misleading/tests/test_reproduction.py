import pytest
from app import require_entries

def test_empty_batch():
    assert require_entries([]) == 0
