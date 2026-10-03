import pytest

from app import workflow


@pytest.fixture(autouse=True)
def _reset_workflow_state():
    workflow._FLOWS.clear()
    yield
    workflow._FLOWS.clear()