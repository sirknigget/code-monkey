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

import re
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
from code_monkey.models.models import GPT_4O_MINI, get_ollama_model, get_openai_model

dotenv.load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MOCK_PROJECT_ROOT = "mock_project"
MOCK_PROJECT_NAME = "crewai_trading_strategy"

# Stable output directory — not cleaned up after tests so output can be inspected
_OUTPUT_DIR = Path("tests/output/real_llm_integration")
_WORKING_DIR = _OUTPUT_DIR / MOCK_PROJECT_NAME


# ---------------------------------------------------------------------------
# Call-logging model wrapper
# ---------------------------------------------------------------------------


class LLMCallLogger(BaseCallbackHandler):
    """LangChain callback that records each chat-model invocation with its path.

    Records entries as:
    - "file:<relative_path>" for file summarisation calls
    - "module:<relative_path>" for module summarisation calls (root module = "root")
    - "project" for project summarisation calls

    Paths are relative to the working directory provided at construction.
    """

    def __init__(self, working_dir: Path) -> None:
        super().__init__()
        self.call_log: list[str] = []
        self._working_dir = working_dir

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
            match = re.search(r"^Module:\s*(.+)$", content, re.MULTILINE)
            if match:
                path = Path(match.group(1).strip())
                try:
                    rel = path.relative_to(self._working_dir)
                    name = str(rel) if str(rel) != "." else "root"
                except ValueError:
                    name = path.name
            else:
                name = "unknown"
            self.call_log.append(f"module:{name}")
        elif "Create a project structure overview" in content:
            self.call_log.append("project")
        else:
            match = re.search(r"^File:\s*(.+)$", content, re.MULTILINE)
            if match:
                path = Path(match.group(1).strip())
                try:
                    rel = path.relative_to(self._working_dir)
                    name = str(rel)
                except ValueError:
                    name = path.name
            else:
                name = "unknown"
            self.call_log.append(f"file:{name}")


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
    call_logger = LLMCallLogger(working_dir)
    llm = get_openai_model(model = GPT_4O_MINI).with_config(callbacks=[call_logger])
    return ProjectMapper(working_dir, Summarizer(llm)), call_logger


def _cache(working_dir: Path) -> CacheManager:
    return CacheManager(working_dir)


def _assert_before(log: list[str], first: str, second: str) -> None:
    """Assert that `first` appears before `second` in the call log."""
    assert log.index(first) < log.index(second), (
        f"Expected {first!r} before {second!r}, got log: {log}"
    )


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

        # LLM call counts: 23 files, 11 modules, 1 project
        log = call_logger.call_log
        file_calls = [e for e in log if e.startswith("file:")]
        module_calls = [e for e in log if e.startswith("module:")]
        assert len(file_calls) == 23
        assert len(module_calls) == 11
        assert log[-1] == "project"

        # Dependency ordering: each file must appear before its containing module,
        # and each child module must appear before its parent module.
        # Parallel calls within the same level may appear in any order.
        _assert_before(log, "file:output/trading_strategy_implementation.py", "module:output")

        _assert_before(
            log,
            "file:src/crewai_trading_strategy/crews/dummy_developer_crew/dummy_crew.py",
            "module:src/crewai_trading_strategy/crews/dummy_developer_crew",
        )
        _assert_before(
            log,
            "file:src/crewai_trading_strategy/crews/trading_strategy_crew/trading_strategy_crew.py",
            "module:src/crewai_trading_strategy/crews/trading_strategy_crew",
        )
        _assert_before(
            log,
            "module:src/crewai_trading_strategy/crews/dummy_developer_crew",
            "module:src/crewai_trading_strategy/crews",
        )
        _assert_before(
            log,
            "module:src/crewai_trading_strategy/crews/trading_strategy_crew",
            "module:src/crewai_trading_strategy/crews",
        )

        _assert_before(
            log,
            "file:src/crewai_trading_strategy/guardrails/backtester_guardrail.py",
            "module:src/crewai_trading_strategy/guardrails",
        )

        _assert_before(
            log,
            "file:src/crewai_trading_strategy/tools/custom_tool.py",
            "module:src/crewai_trading_strategy/tools",
        )

        _assert_before(
            log,
            "module:src/crewai_trading_strategy/crews",
            "module:src/crewai_trading_strategy",
        )
        _assert_before(
            log,
            "module:src/crewai_trading_strategy/guardrails",
            "module:src/crewai_trading_strategy",
        )
        _assert_before(
            log,
            "module:src/crewai_trading_strategy/tools",
            "module:src/crewai_trading_strategy",
        )
        _assert_before(
            log,
            "file:src/crewai_trading_strategy/constants.py",
            "module:src/crewai_trading_strategy",
        )

        _assert_before(log, "file:src/utils/code_utils.py", "module:src/utils")
        _assert_before(log, "file:src/utils/strategy_backtester.py", "module:src/utils")

        _assert_before(log, "module:src/crewai_trading_strategy", "module:src")
        _assert_before(log, "module:src/utils", "module:src")

        _assert_before(log, "file:tests/test_historical_prices.py", "module:tests")

        _assert_before(log, "module:output", "module:root")
        _assert_before(log, "module:src", "module:root")
        _assert_before(log, "module:tests", "module:root")
        _assert_before(log, "module:root", "project")


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

        # LLM call counts: 2 files, 4 modules, 1 project
        log = call_logger.call_log
        file_calls = [e for e in log if e.startswith("file:")]
        module_calls = [e for e in log if e.startswith("module:")]
        assert len(file_calls) == 2
        assert len(module_calls) == 4
        assert log[-1] == "project"

        # Dependency ordering for incremental re-summarisation.
        # Parallel calls (the two file calls) may appear in any order.
        _assert_before(
            log,
            "file:src/crewai_trading_strategy/constants.py",
            "module:src/crewai_trading_strategy",
        )
        _assert_before(log, "file:src/utils/new_helper.py", "module:src/utils")
        _assert_before(log, "module:src/crewai_trading_strategy", "module:src")
        _assert_before(log, "module:src/utils", "module:src")
        _assert_before(log, "module:src", "module:root")
        _assert_before(log, "module:root", "project")
