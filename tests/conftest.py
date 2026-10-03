# Shared test configuration — ensures isolation across all test files

import pytest
from app import workflow


@pytest.fixture(autouse=True)
def _clear_flows():
    """Clear workflow state before every test."""
    workflow._FLOWS.clear()
    yield
    workflow._FLOWS.clear()