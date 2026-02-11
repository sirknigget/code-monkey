"""Integration tests for ProjectMapper with a real file system and a mock LLM.

Tests run against a full working copy of the mock project. The only mock is
the LLM — all other components (ProjectFileHashes, CacheManager, ProjectStructure,
Summarizer) are real.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from code_monkey.agents.project_librarian.cache_manager import CacheManager
from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
from code_monkey.agents.project_librarian.summarizer import Summarizer

# ---------------------------------------------------------------------------
# Deterministic mock LLM
# ---------------------------------------------------------------------------


def _make_mock_llm() -> MagicMock:
    """Return a mock LLM whose responses encode the summarized name.

    Rules:
    - File prompts   → "file-summary:<filename>"   (e.g. "file-summary:constants.py")
    - Module prompts → "module-summary:<dirname>"  (e.g. "module-summary:utils")
    - Project prompt → "project-summary"
    """
    llm = MagicMock(spec=BaseChatModel)
    llm.with_retry.return_value = llm

    def _invoke(prompt_value, config=None, **kwargs) -> AIMessage:
        text = prompt_value.to_messages()[0].content

        if "Summarize this code file" in text:
            match = re.search(r"^File:\s*(.+)$", text, re.MULTILINE)
            filepath = match.group(1).strip() if match else "unknown"
            filename = Path(filepath).name
            return AIMessage(content=f"file-summary:{filename}")

        if "Summarize this Python module" in text:
            match = re.search(r"^Module:\s*(.+)$", text, re.MULTILINE)
            module_path = match.group(1).strip() if match else "unknown"
            module_name = Path(module_path).name
            return AIMessage(content=f"module-summary:{module_name}")

        return AIMessage(content="project-summary")

    llm.invoke.side_effect = _invoke
    return llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mapper(working_dir: Path) -> ProjectMapper:
    return ProjectMapper(working_dir, Summarizer(_make_mock_llm()))


def _cache(working_dir: Path) -> CacheManager:
    return CacheManager(working_dir)


# ---------------------------------------------------------------------------
# TestInitialMapping
# ---------------------------------------------------------------------------


class TestInitialMapping:
    """First run: no cache exists, all files must be summarized and persisted."""

    def test_cache_files_created_with_expected_content(
        self, mock_project_working_copy: Path
    ) -> None:
        _make_mapper(mock_project_working_copy).map_project()

        cache = _cache(mock_project_working_copy)
        context = cache.load_code_context()
        project_ctx = cache.load_project_context()
        hashes = cache.load_hashes()

        # Project-level outputs
        assert project_ctx == "project-summary"
        assert len(hashes) > 0

        # Root context exists and has a summary
        assert context is not None
        assert context.summary is not None

        # Top-level submodules discovered
        assert "src" in context.submodules
        assert "tests" in context.submodules

        # src/utils module summarized
        utils = context.submodules["src"].submodules["utils"]
        assert utils.summary == "module-summary:utils"

        # A specific file in src/utils has a file-level summary
        assert "code_utils.py" in utils.files
        assert utils.files["code_utils.py"].summary == "file-summary:code_utils.py"

        # Deeply nested module: src/crewai_trading_strategy/tools
        tools = (
            context.submodules["src"]
            .submodules["crewai_trading_strategy"]
            .submodules["tools"]
        )
        assert tools.summary == "module-summary:tools"
        assert "custom_tool.py" in tools.files
        assert tools.files["custom_tool.py"].summary == "file-summary:custom_tool.py"

        # Hashes contain the files that were summarized
        assert any("constants.py" in path for path in hashes)


# ---------------------------------------------------------------------------
# TestCompositeFileChanges
# ---------------------------------------------------------------------------


class TestCompositeFileChanges:
    """Second run after composite changes: modify, add, and delete in one step."""

    def test_modified_added_deleted_files_reflected_in_cache(
        self, mock_project_working_copy: Path
    ) -> None:
        # --- Initial mapping ---
        _make_mapper(mock_project_working_copy).map_project()

        # Capture the summary of an unchanged file before the second run
        cache = _cache(mock_project_working_copy)
        context_after_first = cache.load_code_context()
        date_utils_summary_before = (
            context_after_first.submodules["src"]
            .submodules["utils"]
            .files["date_utils.py"]
            .summary
        )

        # --- Apply composite changes ---
        # 1. Modify an existing file
        constants_path = (
            mock_project_working_copy
            / "src"
            / "crewai_trading_strategy"
            / "constants.py"
        )
        constants_path.write_text("MODIFIED_CONSTANT = 99", encoding="utf-8")

        # 2. Add a new file
        new_file_path = mock_project_working_copy / "src" / "utils" / "new_helper.py"
        new_file_path.write_text("def new_helper(): pass", encoding="utf-8")

        # 3. Delete an existing file
        deleted_path = mock_project_working_copy / "src" / "utils" / "code_utils.py"
        deleted_path.unlink()

        # --- Second mapping ---
        _make_mapper(mock_project_working_copy).map_project()

        cache2 = _cache(mock_project_working_copy)
        context2 = cache2.load_code_context()

        src_module = context2.submodules["src"]
        pkg = src_module.submodules["crewai_trading_strategy"]
        utils = src_module.submodules["utils"]

        # Modified file gets a fresh summary (same deterministic content since filename unchanged)
        assert pkg.files["constants.py"].summary == "file-summary:constants.py"

        # Added file is present with a summary
        assert "new_helper.py" in utils.files
        assert utils.files["new_helper.py"].summary == "file-summary:new_helper.py"

        # Deleted file is absent
        assert "code_utils.py" not in utils.files

        # Unchanged file retains its original summary
        assert utils.files["date_utils.py"].summary == date_utils_summary_before

        # Hashes no longer contain the deleted file
        hashes2 = cache2.load_hashes()
        assert not any("code_utils.py" in path for path in hashes2)

        # Hashes contain the new file
        assert any("new_helper.py" in path for path in hashes2)
