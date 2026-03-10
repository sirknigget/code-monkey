"""Real LLM integration tests for ProjectMapper.

These tests use a real local Ollama model and a real filesystem.
They are excluded from the default pytest run because they:
  - Require a running Ollama instance
  - Make real LLM calls (slow)

Run explicitly with:
    uv run pytest -m real_llm -v

Output is intentionally left in tests/output/real_llm_integration/ after
the test completes so it can be manually inspected. State is reset (deleted)
at the START of each test, not the end.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from uuid import UUID

import dotenv
import pytest
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage

from code_monkey.agents.project_librarian.cache_manager import CacheManager
from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.models.models import get_ollama_model

dotenv.load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MOCK_PROJECT_ROOT = "mock_project"
MOCK_PROJECT_NAME = "crewai_trading_strategy"

# Stable output directory — not cleaned up after tests so output can be inspected
_OUTPUT_DIR = Path("tests/output/real_llm_integration")
_WORKING_DIR = _OUTPUT_DIR / MOCK_PROJECT_NAME

# Expected LLM call sequences derived from the mock project structure and the
# bottom-up traversal order in ProjectMapper._summarize_bottom_up.
#
# File discovery returns paths sorted alphabetically. The module tree is built
# in that insertion order. Traversal: recurse submodules first, then summarize
# each file in the module, then summarize the module itself. Project summary
# is always last.
_EXPECTED_INITIAL_CALLS = [
    "file",
    "module",  # output/ (1 file)
    "file",
    "module",  # crews/dummy_developer_crew/ (1 file)
    "file",
    "module",  # crews/trading_strategy_crew/ (1 file)
    "module",  # crews/ (no direct files)
    "file",
    "module",  # guardrails/ (1 file)
    "file",
    "file",
    "file",
    "file",
    "file",
    "module",  # tools/ (5 files)
    "file",
    "file",
    "file",
    "file",
    "file",
    "module",  # crewai_trading_strategy/ (5 files)
    "file",
    "file",
    "file",
    "file",
    "file",
    "file",
    "module",  # src/utils/ (6 files)
    "module",  # src/ (no direct files)
    "file",
    "file",
    "file",
    "module",  # tests/ (3 files)
    "module",  # root (no direct files)
    "project",
]

_EXPECTED_SECOND_CALLS = [
    "file",
    "module",  # constants.py re-summarised → crewai_trading_strategy/ re-summarised
    "file",
    "module",  # new_helper.py summarised → src/utils/ re-summarised
    "module",  # src/ re-summarised
    "module",  # root re-summarised
    "project",
]


# ---------------------------------------------------------------------------
# Call-logging model wrapper
# ---------------------------------------------------------------------------


class LLMCallLogger(BaseCallbackHandler):
    """LangChain callback that records each chat-model invocation type.

    Distinguishes file, module, and project summarisation calls by inspecting
    distinctive phrases present in the formatted prompt templates.
    """

    def __init__(self) -> None:
        super().__init__()
        self.call_log: list[str] = []

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        content = messages[0][0].content if messages and messages[0] else ""
        if "Summarize this Python module" in content:
            self.call_log.append("module")
        elif "Create a project structure overview" in content:
            self.call_log.append("project")
        else:
            self.call_log.append("file")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mock_project_template_root(pytestconfig) -> Path:
    return pytestconfig.rootpath / MOCK_PROJECT_ROOT / "template" / MOCK_PROJECT_NAME


@pytest.fixture
def real_llm_working_dir(mock_project_template_root: Path) -> Path:
    """Provide a stable working copy of the mock project for real LLM tests.

    The working copy is placed at tests/output/real_llm_integration/ which is
    gitignored. State is reset at the start of each test.
    """
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Reset: remove previous working copy and recreate from template
    if _WORKING_DIR.exists():
        shutil.rmtree(_WORKING_DIR)
    shutil.copytree(mock_project_template_root, _WORKING_DIR)

    # No teardown — output is left for manual inspection
    return _WORKING_DIR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mapper(working_dir: Path) -> tuple[ProjectMapper, LLMCallLogger]:
    call_logger = LLMCallLogger()
    llm = get_ollama_model().with_config(callbacks=[call_logger])
    return ProjectMapper(working_dir, Summarizer(llm)), call_logger


def _cache(working_dir: Path) -> CacheManager:
    return CacheManager(working_dir)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_llm
class TestRealLlmInitialMapping:
    """First run: no cache exists; the full pipeline runs against a real LLM.

    Assertions are structural only — content is non-deterministic.
    """

    def test_cache_files_created_with_expected_structure(
        self, real_llm_working_dir: Path
    ) -> None:
        mapper, call_logger = _make_mapper(real_llm_working_dir)
        mapper.map_project()

        cache = _cache(real_llm_working_dir)
        context = cache.load_code_context()
        project_ctx = cache.load_project_context()
        hashes = cache.load_hashes()

        # Cache files must exist and contain data
        assert project_ctx is not None
        assert isinstance(project_ctx, str)
        assert len(project_ctx) > 0

        assert len(hashes) > 0

        # Root context must exist with a non-empty summary
        assert context is not None
        assert isinstance(context.summary, str)
        assert len(context.summary) > 0

        # Top-level submodules discovered
        assert "src" in context.submodules
        assert "tests" in context.submodules

        # src/utils module must exist and have a non-empty summary
        utils = context.submodules["src"].submodules["utils"]
        assert isinstance(utils.summary, str)
        assert len(utils.summary) > 0

        # A specific file in src/utils has a non-empty summary
        assert "code_utils.py" in utils.files
        assert isinstance(utils.files["code_utils.py"].summary, str)
        assert len(utils.files["code_utils.py"].summary) > 0

        # Deeply nested module: src/crewai_trading_strategy/tools
        tools = (
            context.submodules["src"]
            .submodules["crewai_trading_strategy"]
            .submodules["tools"]
        )
        assert isinstance(tools.summary, str)
        assert len(tools.summary) > 0
        assert "custom_tool.py" in tools.files
        assert isinstance(tools.files["custom_tool.py"].summary, str)
        assert len(tools.files["custom_tool.py"].summary) > 0

        # Hashes contain at least one known file
        assert any("constants.py" in path for path in hashes)

        # Exact LLM call sequence matches bottom-up traversal order
        assert call_logger.call_log == _EXPECTED_INITIAL_CALLS


@pytest.mark.real_llm
class TestRealLlmCompositeFileChanges:
    """Second run after composite changes: modify, add, and delete in one step.

    Assertions are structural only — content is non-deterministic.
    """

    def test_modified_added_deleted_files_reflected_in_cache(
        self, real_llm_working_dir: Path
    ) -> None:
        # --- Initial mapping ---
        mapper1, _ = _make_mapper(real_llm_working_dir)
        mapper1.map_project()

        # --- Apply composite changes ---
        # 1. Modify an existing file
        constants_path = (
            real_llm_working_dir / "src" / "crewai_trading_strategy" / "constants.py"
        )
        constants_path.write_text("MODIFIED_CONSTANT = 99", encoding="utf-8")

        # 2. Add a new file
        new_file_path = real_llm_working_dir / "src" / "utils" / "new_helper.py"
        new_file_path.write_text("def new_helper(): pass", encoding="utf-8")

        # 3. Delete an existing file
        deleted_path = real_llm_working_dir / "src" / "utils" / "code_utils.py"
        deleted_path.unlink()

        # --- Second mapping ---
        mapper2, call_logger = _make_mapper(real_llm_working_dir)
        mapper2.map_project()

        cache2 = _cache(real_llm_working_dir)
        context2 = cache2.load_code_context()

        src_module = context2.submodules["src"]
        pkg = src_module.submodules["crewai_trading_strategy"]
        utils = src_module.submodules["utils"]

        # Modified file has a non-empty summary
        assert isinstance(pkg.files["constants.py"].summary, str)
        assert len(pkg.files["constants.py"].summary) > 0

        # Added file is present with a non-empty summary
        assert "new_helper.py" in utils.files
        assert isinstance(utils.files["new_helper.py"].summary, str)
        assert len(utils.files["new_helper.py"].summary) > 0

        # Deleted file is absent from the context
        assert "code_utils.py" not in utils.files

        # Hashes no longer contain the deleted file
        hashes2 = cache2.load_hashes()
        assert not any("code_utils.py" in path for path in hashes2)

        # Hashes contain the new file
        assert any("new_helper.py" in path for path in hashes2)

        # Exact LLM call sequence matches incremental re-summarisation order
        assert call_logger.call_log == _EXPECTED_SECOND_CALLS
