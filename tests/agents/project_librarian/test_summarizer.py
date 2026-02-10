"""Tests for the Summarizer class."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.language_models import BaseChatModel

from code_monkey.agents.project_librarian.cache_manager import ModuleContext
from code_monkey.agents.project_librarian.summarizer import Summarizer


@pytest.fixture
def mock_llm():
    """Create a mock BaseChatModel that supports with_retry."""
    llm = MagicMock(spec=BaseChatModel)
    llm.with_retry.return_value = llm
    return llm


@pytest.fixture
def summarizer(mock_llm):
    """Create a Summarizer instance with mock LLM and mocked chains."""
    s = Summarizer(mock_llm)
    # Replace chains with controllable mocks after construction
    s._file_chain = MagicMock()
    s._file_chain.invoke.return_value = "File summary"
    s._module_chain = MagicMock()
    s._module_chain.invoke.return_value = "Module summary"
    s._project_chain = MagicMock()
    s._project_chain.invoke.return_value = "Project summary"
    return s


class TestSummarizerInit:
    """Tests for Summarizer initialization."""

    def test_wraps_llm_with_retry(self, mock_llm):
        """Test that __init__ wraps the LLM with retry behavior."""
        Summarizer(mock_llm)
        mock_llm.with_retry.assert_called_once_with(stop_after_attempt=Summarizer.MAX_RETRIES)

    def test_creates_file_chain(self, mock_llm):
        """Test that __init__ creates the file summary chain."""
        s = Summarizer(mock_llm)
        assert s._file_chain is not None

    def test_creates_module_chain(self, mock_llm):
        """Test that __init__ creates the module summary chain."""
        s = Summarizer(mock_llm)
        assert s._module_chain is not None

    def test_creates_project_chain(self, mock_llm):
        """Test that __init__ creates the project summary chain."""
        s = Summarizer(mock_llm)
        assert s._project_chain is not None

    def test_max_retries_constant(self):
        """Test MAX_RETRIES is set to expected value."""
        assert Summarizer.MAX_RETRIES == 3


class TestSummarizeFile:
    """Tests for Summarizer.summarize_file."""

    def test_passes_filepath_to_chain(self, summarizer):
        """Test that summarize_file passes correct filepath to chain."""
        summarizer.summarize_file(Path("/test/file.py"), "def foo(): pass")
        call_args = summarizer._file_chain.invoke.call_args[0][0]
        assert call_args["filepath"] == "/test/file.py"

    def test_passes_code_to_chain(self, summarizer):
        """Test that summarize_file passes correct code to chain."""
        code = "def foo(): return 42"
        summarizer.summarize_file(Path("/test/file.py"), code)
        call_args = summarizer._file_chain.invoke.call_args[0][0]
        assert call_args["code"] == code

    def test_default_parent_context_is_none_string(self, summarizer):
        """Test that default parent_context is '(none)' when None passed."""
        summarizer.summarize_file(Path("/test/file.py"), "code")
        call_args = summarizer._file_chain.invoke.call_args[0][0]
        assert call_args["parent_context"] == "(none)"

    def test_passes_explicit_parent_context(self, summarizer):
        """Test that explicit parent_context is passed through."""
        summarizer.summarize_file(Path("/test/file.py"), "code", parent_context="Module context")
        call_args = summarizer._file_chain.invoke.call_args[0][0]
        assert call_args["parent_context"] == "Module context"

    def test_passes_max_lines_to_chain(self, summarizer):
        """Test that summarize_file passes MAX_FILE_SUMMARY_LINES to chain."""
        summarizer.summarize_file(Path("/test/file.py"), "code")
        call_args = summarizer._file_chain.invoke.call_args[0][0]
        assert call_args["max_lines"] == Summarizer.MAX_FILE_SUMMARY_LINES

    def test_output_is_stripped(self, summarizer):
        """Test that the returned summary has whitespace stripped."""
        summarizer._file_chain.invoke.return_value = "  Summary with spaces  "
        result = summarizer.summarize_file(Path("/test/file.py"), "code")
        assert result == "Summary with spaces"

    def test_filepath_converted_to_string(self, summarizer):
        """Test that Path is converted to string for the chain."""
        summarizer.summarize_file(Path("/some/deep/path/module.py"), "code")
        call_args = summarizer._file_chain.invoke.call_args[0][0]
        assert isinstance(call_args["filepath"], str)
        assert call_args["filepath"] == "/some/deep/path/module.py"


class TestSummarizeModule:
    """Tests for Summarizer.summarize_module."""

    def test_passes_module_path_to_chain(self, summarizer):
        """Test that summarize_module passes correct module_path."""
        file_info = Summarizer.FileInfo(
            filepath=Path("/project/utils/helper.py"),
            summary="Helper utilities",
            structure="def helper(): ...",
        )
        summarizer.summarize_module(Path("/project/utils"), [file_info])
        call_args = summarizer._module_chain.invoke.call_args[0][0]
        assert call_args["module_path"] == "/project/utils"

    def test_passes_default_parent_context(self, summarizer):
        """Test that default parent_context is '(none)' for module."""
        file_info = Summarizer.FileInfo(
            filepath=Path("/project/mod.py"),
            summary="A module",
            structure="class Foo: ...",
        )
        summarizer.summarize_module(Path("/project"), [file_info])
        call_args = summarizer._module_chain.invoke.call_args[0][0]
        assert call_args["parent_context"] == "(none)"

    def test_passes_explicit_parent_context(self, summarizer):
        """Test that explicit parent_context is passed through."""
        file_info = Summarizer.FileInfo(
            filepath=Path("/project/mod.py"),
            summary="A module",
            structure="class Foo: ...",
        )
        summarizer.summarize_module(Path("/project"), [file_info], parent_context="Root context")
        call_args = summarizer._module_chain.invoke.call_args[0][0]
        assert call_args["parent_context"] == "Root context"

    def test_passes_max_lines_to_chain(self, summarizer):
        """Test that summarize_module passes MAX_MODULE_SUMMARY_LINES."""
        file_info = Summarizer.FileInfo(
            filepath=Path("/project/mod.py"),
            summary="A module",
            structure="def func(): ...",
        )
        summarizer.summarize_module(Path("/project"), [file_info])
        call_args = summarizer._module_chain.invoke.call_args[0][0]
        assert call_args["max_lines"] == Summarizer.MAX_MODULE_SUMMARY_LINES

    def test_formats_multiple_file_infos_with_separator(self, summarizer):
        """Test that multiple FileInfo entries are joined with '---' separator."""
        file_infos = [
            Summarizer.FileInfo(
                filepath=Path("/project/a.py"),
                summary="File A summary",
                structure="class A: ...",
            ),
            Summarizer.FileInfo(
                filepath=Path("/project/b.py"),
                summary="File B summary",
                structure="class B: ...",
            ),
        ]
        summarizer.summarize_module(Path("/project"), file_infos)
        call_args = summarizer._module_chain.invoke.call_args[0][0]
        file_summaries = call_args["file_summaries"]
        assert "---" in file_summaries

    def test_file_info_filename_appears_in_summaries(self, summarizer):
        """Test that file names appear in the formatted summaries string."""
        file_infos = [
            Summarizer.FileInfo(
                filepath=Path("/project/utils.py"),
                summary="Utility functions",
                structure="def helper(): ...",
            ),
        ]
        summarizer.summarize_module(Path("/project"), file_infos)
        call_args = summarizer._module_chain.invoke.call_args[0][0]
        file_summaries = call_args["file_summaries"]
        assert "utils.py" in file_summaries

    def test_empty_file_infos_produces_empty_summaries(self, summarizer):
        """Test that empty file_infos produces an empty file_summaries string."""
        summarizer.summarize_module(Path("/project"), [])
        call_args = summarizer._module_chain.invoke.call_args[0][0]
        assert call_args["file_summaries"] == ""

    def test_output_is_stripped(self, summarizer):
        """Test that the module summary result is stripped."""
        summarizer._module_chain.invoke.return_value = "\n  Module summary  \n"
        file_info = Summarizer.FileInfo(
            filepath=Path("/project/mod.py"),
            summary="A module",
            structure="def func(): ...",
        )
        result = summarizer.summarize_module(Path("/project"), [file_info])
        assert result == "Module summary"


class TestModuleSummariesFromCodeContext:
    """Tests for Summarizer._module_summaries_from_code_context."""

    def test_root_module_uses_empty_string_as_path(self, summarizer):
        """Test that root module path is empty string."""
        ctx = ModuleContext(summary="Root summary")
        summaries = summarizer._module_summaries_from_code_context(ctx)
        assert len(summaries) >= 1
        assert summaries[0][0] == ""
        assert summaries[0][1] == "Root summary"

    def test_single_submodule_path(self, summarizer):
        """Test that a single submodule builds a correct path."""
        ctx = ModuleContext(
            summary="Root",
            submodules={
                "utils": ModuleContext(summary="Utils module"),
            },
        )
        summaries = summarizer._module_summaries_from_code_context(ctx)
        paths = {path for path, _ in summaries}
        assert "utils" in paths

    def test_nested_submodule_path(self, summarizer):
        """Test that nested submodules build correct paths (e.g., 'pkg/subpkg')."""
        ctx = ModuleContext(
            summary="Root",
            submodules={
                "pkg": ModuleContext(
                    summary="Package",
                    submodules={
                        "subpkg": ModuleContext(summary="Sub-package"),
                    },
                ),
            },
        )
        summaries = summarizer._module_summaries_from_code_context(ctx)
        paths = {path for path, _ in summaries}
        assert "pkg" in paths
        assert "pkg/subpkg" in paths

    def test_extracts_all_summaries_recursively(self, summarizer):
        """Test that all summaries are extracted from the full hierarchy."""
        ctx = ModuleContext(
            summary="Root",
            submodules={
                "a": ModuleContext(
                    summary="Module A",
                    submodules={
                        "b": ModuleContext(summary="Module B"),
                    },
                ),
                "c": ModuleContext(summary="Module C"),
            },
        )
        summaries = summarizer._module_summaries_from_code_context(ctx)
        assert len(summaries) == 4  # root, a, a/b, c
        summary_texts = {s for _, s in summaries}
        assert "Root" in summary_texts
        assert "Module A" in summary_texts
        assert "Module B" in summary_texts
        assert "Module C" in summary_texts

    def test_no_submodules_returns_single_entry(self, summarizer):
        """Test that a context with no submodules returns only root entry."""
        ctx = ModuleContext(summary="Leaf module")
        summaries = summarizer._module_summaries_from_code_context(ctx)
        assert len(summaries) == 1
        assert summaries[0] == ("", "Leaf module")


class TestSummarizeProject:
    """Tests for Summarizer.summarize_project."""

    def test_passes_project_name_to_chain(self, summarizer):
        """Test that summarize_project passes project_name to chain."""
        ctx = ModuleContext(summary="Root summary")
        summarizer.summarize_project("project/\n  src/", ctx, "my-project")
        call_args = summarizer._project_chain.invoke.call_args[0][0]
        assert call_args["project_name"] == "my-project"

    def test_passes_project_structure_to_chain(self, summarizer):
        """Test that summarize_project passes project_structure to chain."""
        ctx = ModuleContext(summary="Root summary")
        structure = "my-project/\n  src/\n  tests/"
        summarizer.summarize_project(structure, ctx, "my-project")
        call_args = summarizer._project_chain.invoke.call_args[0][0]
        assert call_args["project_structure"] == structure

    def test_passes_max_lines_to_chain(self, summarizer):
        """Test that summarize_project passes MAX_PROJECT_SUMMARY_LINES."""
        ctx = ModuleContext(summary="Root summary")
        summarizer.summarize_project("structure", ctx, "project")
        call_args = summarizer._project_chain.invoke.call_args[0][0]
        assert call_args["max_lines"] == Summarizer.MAX_PROJECT_SUMMARY_LINES

    def test_module_summaries_formatted_in_input(self, summarizer):
        """Test that module summaries appear in the formatted input."""
        ctx = ModuleContext(
            summary="Root module summary",
            submodules={
                "utils": ModuleContext(summary="Utils summary"),
            },
        )
        summarizer.summarize_project("structure", ctx, "project")
        call_args = summarizer._project_chain.invoke.call_args[0][0]
        module_summaries = call_args["module_summaries"]
        # module_summaries is a list of formatted strings
        combined = "".join(module_summaries)
        assert "Root module summary" in combined
        assert "Utils summary" in combined

    def test_output_is_stripped(self, summarizer):
        """Test that summarize_project output is stripped."""
        summarizer._project_chain.invoke.return_value = "  Project overview  \n"
        ctx = ModuleContext(summary="Root")
        result = summarizer.summarize_project("structure", ctx, "project")
        assert result == "Project overview"
