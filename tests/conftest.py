"""Test fixtures for template-based testing.

Provides fixtures for copying the crewai_trading_strategy template
to isolated working directories for testing.
"""

import logging
import shutil
from pathlib import Path

import pytest

from code_monkey.utils.log_utils import get_formatted_logger, suppress_noisy_loggers

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
logger = get_formatted_logger(__name__)

suppress_noisy_loggers()

# Path to the mock project root
MOCK_PROJECT_ROOT = "mock_project"
MOCK_PROJECT_NAME = "crewai_trading_strategy"


@pytest.fixture(scope="session")
def mock_project_template_root(pytestconfig) -> Path:
    """Return the path to the crewai_trading_strategy template.

    This is a session-scoped fixture that provides the template root directory.
    Tests should use crewai_working_copy for isolated modifications.
    """
    return pytestconfig.rootpath / MOCK_PROJECT_ROOT / "template" / MOCK_PROJECT_NAME


@pytest.fixture
def mock_project_working_copy(tmp_path, mock_project_template_root: Path) -> Path:
    """Create an isolated working copy of the crewai_trading_strategy template.

    Each test gets its own copy that can be modified without affecting
    the original template. The copy is automatically cleaned up after
    the test completes.
    """
    # Copy template to temp directory
    temp_copy = MOCK_PROJECT_ROOT / tmp_path / MOCK_PROJECT_NAME
    shutil.copytree(mock_project_template_root, temp_copy)

    return temp_copy
