"""Test fixtures for template-based testing.

Provides fixtures for copying the crewai_trading_strategy template
to isolated working directories for testing.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

# Path to the crewai_trading_strategy template
TEMPLATE_ROOT = Path(__file__).parent.parent.parent / "mock_project" / "template" / "crewai_trading_strategy"


@pytest.fixture(scope="session")
def crewai_template_root() -> Path:
    """Return the path to the crewai_trading_strategy template.

    This is a session-scoped fixture that provides the template root directory.
    Tests should use crewai_working_copy for isolated modifications.
    """
    return TEMPLATE_ROOT


@pytest.fixture
def crewai_working_copy(tmp_path, crewai_template_root: Path) -> Path:
    """Create an isolated working copy of the crewai_trading_strategy template.

    Each test gets its own copy that can be modified without affecting
    the original template. The copy is automatically cleaned up after
    the test completes.
    """
    # Copy template to temp directory
    temp_copy = tmp_path / "crewai_trading_strategy"
    shutil.copytree(crewai_template_root, temp_copy)

    yield temp_copy

    # Cleanup is automatic due to tmp_path, but explicit cleanup for safety
    if temp_copy.exists():
        shutil.rmtree(temp_copy)
