"""Tests for the Summarizer class."""

from unittest.mock import MagicMock

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.agents.project_librarian.summarizer_prompts import (
    FILE_SUMMARY_TEMPLATE,
    MODULE_SUMMARY_TEMPLATE,
    PROJECT_SUMMARY_TEMPLATE,
)
from code_monkey.agents.project_librarian.types import ModuleContext


@pytest.fixture
def mock_llm():
    """Create a mock BaseChatModel that returns a fixed response."""
    llm = MagicMock(spec=BaseChatModel)
    llm.with_retry.return_value = llm
    llm.invoke.return_value = AIMessage(content="mock response")
    return llm


@pytest.fixture
def summarizer(mock_llm, tmp_path):
    """Create a Summarizer instance with mock LLM."""
    return Summarizer(mock_llm, tmp_path)


def _prompt_content(mock_llm: MagicMock) -> str:
    """Extract the formatted prompt text sent to the LLM."""
    prompt_value = mock_llm.invoke.call_args[0][0]
    return prompt_value.to_messages()[0].content


class TestSummarizeFile:
    """Tests for Summarizer.summarize_file."""

    def test_returns_stripped_llm_output(self, mock_llm, tmp_path):
        mock_llm.invoke.return_value = AIMessage(content="  File summary  ")
        result = Summarizer(mock_llm, tmp_path).summarize_file(
            tmp_path / "file.py", "def foo(): pass"
        )
        assert result == "File summary"

    def test_prompt(self, summarizer, mock_llm, tmp_path):
        code = "def foo(): return 42"
        summarizer.summarize_file(tmp_path / "file.py", code)
        assert _prompt_content(mock_llm) == FILE_SUMMARY_TEMPLATE.format(
            filepath="file.py",
            code=code,
            max_lines=Summarizer.MAX_FILE_SUMMARY_LINES,
        )


class TestSummarizeModule:
    """Tests for Summarizer.summarize_module."""

    def test_returns_stripped_llm_output(self, mock_llm, tmp_path):
        mock_llm.invoke.return_value = AIMessage(content="\n  Module summary  \n")
        file_info = Summarizer.FileInfo(
            filepath=tmp_path / "mod.py",
            summary="A module",
        )
        submodule_info = Summarizer.FileInfo(
            filepath=tmp_path / "utils",
            summary="A helper module",
        )
        result = Summarizer(mock_llm, tmp_path).summarize_module(
            tmp_path, [file_info], [submodule_info]
        )
        assert result == "Module summary"

    def test_prompt(self, summarizer, mock_llm, tmp_path):
        file_infos = [
            Summarizer.FileInfo(
                filepath=tmp_path / "pkg" / "a.py",
                summary="A summary",
            ),
            Summarizer.FileInfo(
                filepath=tmp_path / "pkg" / "b.py",
                summary="B summary",
            ),
        ]
        submodule_infos = [
            Summarizer.FileInfo(
                filepath=tmp_path / "pkg" / "utils",
                summary="Utils summary",
            )
        ]
        summarizer.summarize_module(
            tmp_path / "pkg" / "utils", file_infos, submodule_infos
        )
        file_summaries = (
            "File: a.py -> Summary:\nA summary\n---\nFile: b.py -> Summary:\nB summary"
        )
        assert _prompt_content(mock_llm) == MODULE_SUMMARY_TEMPLATE.format(
            module_path="pkg/utils",
            file_summaries=file_summaries,
            submodule_summaries="File: utils -> Summary:\nUtils summary",
            max_lines=Summarizer.MAX_MODULE_SUMMARY_LINES,
        )


class TestModuleSummariesFromCodeContext:
    """Tests for Summarizer._module_summaries_from_code_context."""

    def test_root_module_uses_empty_string_as_path(self, summarizer):
        summaries = summarizer._module_summaries_from_code_context(
            ModuleContext(summary="Root summary")
        )
        assert summaries[0] == ("", "Root summary")

    def test_single_submodule_path(self, summarizer):
        ctx = ModuleContext(
            summary="Root",
            submodules={"utils": ModuleContext(summary="Utils module")},
        )
        paths = {
            path for path, _ in summarizer._module_summaries_from_code_context(ctx)
        }
        assert "utils" in paths

    def test_nested_submodule_path(self, summarizer):
        ctx = ModuleContext(
            summary="Root",
            submodules={
                "pkg": ModuleContext(
                    summary="Package",
                    submodules={"subpkg": ModuleContext(summary="Sub-package")},
                ),
            },
        )
        paths = {
            path for path, _ in summarizer._module_summaries_from_code_context(ctx)
        }
        assert "pkg" in paths
        assert "pkg/subpkg" in paths

    def test_extracts_all_summaries_recursively(self, summarizer):
        ctx = ModuleContext(
            summary="Root",
            submodules={
                "a": ModuleContext(
                    summary="Module A",
                    submodules={"b": ModuleContext(summary="Module B")},
                ),
                "c": ModuleContext(summary="Module C"),
            },
        )
        summaries = summarizer._module_summaries_from_code_context(ctx)
        assert len(summaries) == 4
        assert {s for _, s in summaries} == {"Root", "Module A", "Module B", "Module C"}

    def test_no_submodules_returns_single_entry(self, summarizer):
        summaries = summarizer._module_summaries_from_code_context(
            ModuleContext(summary="Leaf module")
        )
        assert summaries == [("", "Leaf module")]


class TestSummarizeProject:
    """Tests for Summarizer.summarize_project."""

    def test_returns_stripped_llm_output(self, mock_llm, tmp_path):
        mock_llm.invoke.return_value = AIMessage(content="  Project overview  \n")
        result = Summarizer(mock_llm, tmp_path).summarize_project(
            "structure", ModuleContext(summary="Root"), "project"
        )
        assert result == "Project overview"

    def test_prompt(self, summarizer, mock_llm):
        ctx = ModuleContext(
            summary="Root module summary",
            submodules={"utils": ModuleContext(summary="Utils summary")},
        )
        structure = "my-project/\n  src/\n  tests/"
        summarizer.summarize_project(structure, ctx, "my-project")

        summary_parts = summarizer._module_summaries_from_code_context(ctx)
        module_summaries = [
            f"{path}:\n{summary}\n\n" for path, summary in summary_parts
        ]
        assert _prompt_content(mock_llm) == PROJECT_SUMMARY_TEMPLATE.format(
            module_summaries=module_summaries,
            project_name="my-project",
            project_structure=structure,
            max_lines=Summarizer.MAX_PROJECT_SUMMARY_LINES,
        )
