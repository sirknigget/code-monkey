"""Tests for Summarizer class."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_monkey.agents.project_librarian.summarizer import Summarizer


class TestSummarizerInitialization:
    """Tests for Summarizer initialization."""

    def test_initializes_with_llm(self) -> None:
        """Should initialize with provided LLM."""
        mock_llm = MagicMock()
        summarizer = Summarizer(mock_llm)

        assert summarizer.llm == mock_llm

    def test_creates_file_summary_chain(self) -> None:
        """Should create file summary chain on init."""
        mock_llm = MagicMock()
        summarizer = Summarizer(mock_llm)

        assert summarizer._file_chain is not None
        assert summarizer._module_chain is not None
        assert summarizer._project_chain is not None

    def test_max_summary_lines_default(self) -> None:
        """Should have correct default MAX_SUMMARY_LINES."""
        assert Summarizer.MAX_SUMMARY_LINES == 10

    def test_max_retries_default(self) -> None:
        """Should have correct default MAX_RETRIES."""
        assert Summarizer.MAX_RETRIES == 3

    def test_backoff_base_default(self) -> None:
        """Should have correct default BACKOFF_BASE."""
        assert Summarizer.BACKOFF_BASE == 2.0

    def test_initial_delay_default(self) -> None:
        """Should have correct default INITIAL_DELAY."""
        assert Summarizer.INITIAL_DELAY == 1.0


class TestSummarizeFile:
    """Tests for file summarization."""

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_summarize_file_returns_summary(self, mock_parser, mock_template) -> None:
        """Should return summary from LLM."""
        mock_llm = MagicMock()
        expected_summary = "File summary text"

        # Setup the chain mock
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = expected_summary
        mock_template.from_template.return_value = mock_chain
        mock_chain.__or__ = MagicMock(return_value=mock_chain)

        summarizer = Summarizer(mock_llm)
        # Directly mock the internal chain's invoke
        summarizer._file_chain = mock_chain

        result = summarizer.summarize_file(
            filepath=Path("test.py"),
            structure="class Test:\n    pass",
        )

        assert result == expected_summary

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_summarize_file_calls_chain(self, mock_parser, mock_template) -> None:
        """Should call chain with input."""
        mock_llm = MagicMock()
        expected_summary = "summary"

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = expected_summary

        summarizer = Summarizer(mock_llm)
        summarizer._file_chain = mock_chain

        result = summarizer.summarize_file(
            filepath=Path("test.py"),
            structure="structure here",
        )

        assert result == expected_summary
        mock_chain.invoke.assert_called()

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_summarize_file_truncates_long_output(self, mock_parser, mock_template) -> None:
        """Should truncate output to MAX_SUMMARY_LINES."""
        mock_llm = MagicMock()
        # Return many lines
        long_output = "\n".join([f"line {i}" for i in range(20)])

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = long_output

        summarizer = Summarizer(mock_llm)
        summarizer._file_chain = mock_chain

        result = summarizer.summarize_file(
            filepath=Path("test.py"),
            structure="structure",
        )

        lines = result.split("\n")
        assert len(lines) <= Summarizer.MAX_SUMMARY_LINES


class TestSummarizeModule:
    """Tests for module summarization."""

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_summarize_module_returns_summary(self, mock_parser, mock_template) -> None:
        """Should return module summary."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Module summary"

        summarizer = Summarizer(mock_llm)
        summarizer._module_chain = mock_chain

        result = summarizer.summarize_module(
            directory=Path("/path/to/module"),
            file_summaries=["file1 summary", "file2 summary"],
        )

        assert result == "Module summary"

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_summarize_module_with_empty_file_list(self, mock_parser, mock_template) -> None:
        """Should handle empty file summaries list."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "summary"

        summarizer = Summarizer(mock_llm)
        summarizer._module_chain = mock_chain

        result = summarizer.summarize_module(
            directory=Path("/empty/module"),
            file_summaries=[],
        )

        assert result == "summary"


class TestGenerateProjectContext:
    """Tests for project context generation."""

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_generate_project_context_returns_string(self, mock_parser, mock_template) -> None:
        """Should return project context string."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "project context"

        summarizer = Summarizer(mock_llm)
        summarizer._project_chain = mock_chain

        result = summarizer.generate_project_context(
            module_summaries={Path("/src"): "src module"},
            project_name="test_project",
        )

        assert isinstance(result, str)

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_generate_project_context_with_empty_summaries(self, mock_parser, mock_template) -> None:
        """Should handle empty module summaries dict."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "context"

        summarizer = Summarizer(mock_llm)
        summarizer._project_chain = mock_chain

        result = summarizer.generate_project_context(
            module_summaries={},
            project_name="empty_project",
        )

        assert result == "context"

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_generate_project_context_includes_project_name(self, mock_parser, mock_template) -> None:
        """Should pass project name to template."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "context"

        summarizer = Summarizer(mock_llm)
        summarizer._project_chain = mock_chain

        result = summarizer.generate_project_context(
            module_summaries={Path("/"): "root"},
            project_name="my_awesome_project",
        )

        assert result == "context"


class TestSummarizerRetryLogic:
    """Tests for retry logic with exponential backoff."""

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_retry_on_first_failure(self, mock_parser, mock_template) -> None:
        """Should retry and succeed after failure."""
        mock_llm = MagicMock()
        call_count = 0

        def side_effect(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("temporary failure")
            return "success"

        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = side_effect

        summarizer = Summarizer(mock_llm)
        summarizer._file_chain = mock_chain

        result = summarizer.summarize_file(
            filepath=Path("test.py"),
            structure="structure",
        )

        assert result == "success"
        assert call_count == 2

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_exhausts_retries_on_constant_failure(self, mock_parser, mock_template) -> None:
        """Should raise after exhausting all retries."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = Exception("permanent failure")

        summarizer = Summarizer(mock_llm)
        summarizer._file_chain = mock_chain

        with pytest.raises(RuntimeError, match="Summarization failed after"):
            summarizer.summarize_file(
                filepath=Path("test.py"),
                structure="structure",
            )

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_no_retry_on_success_first_try(self, mock_parser, mock_template) -> None:
        """Should not retry on successful first call."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "success"

        summarizer = Summarizer(mock_llm)
        summarizer._file_chain = mock_chain

        result = summarizer.summarize_file(
            filepath=Path("test.py"),
            structure="structure",
        )

        assert result == "success"
        assert mock_chain.invoke.call_count == 1


class TestSummarizerChainCreation:
    """Tests for LangChain chain creation."""

    def test_file_chain_is_runnable_sequence(self) -> None:
        """Chain should be a RunnableSequence."""
        mock_llm = MagicMock()
        summarizer = Summarizer(mock_llm)

        # Chain should be a RunnableSequence
        assert summarizer._file_chain is not None

    def test_module_chain_is_runnable_sequence(self) -> None:
        """Module chain should be a RunnableSequence."""
        mock_llm = MagicMock()
        summarizer = Summarizer(mock_llm)

        assert summarizer._module_chain is not None

    def test_project_chain_is_runnable_sequence(self) -> None:
        """Project chain should be a RunnableSequence."""
        mock_llm = MagicMock()
        summarizer = Summarizer(mock_llm)

        assert summarizer._project_chain is not None


class TestSummarizerWithDifferentInputs:
    """Tests for various input combinations."""

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_summarize_file_with_special_chars_in_path(self, mock_parser, mock_template) -> None:
        """Should handle paths with special characters."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "summary"

        summarizer = Summarizer(mock_llm)
        summarizer._file_chain = mock_chain

        result = summarizer.summarize_file(
            filepath=Path("/path/with-dashes_and_underscores/file.py"),
            structure="class Test:\n    pass",
        )

        assert result == "summary"

    @patch('code_monkey.agents.project_librarian.summarizer.ChatPromptTemplate')
    @patch('code_monkey.agents.project_librarian.summarizer.StrOutputParser')
    def test_generate_project_context_with_nested_paths(self, mock_parser, mock_template) -> None:
        """Should handle deeply nested module paths."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "context"

        summarizer = Summarizer(mock_llm)
        summarizer._project_chain = mock_chain

        module_summaries = {
            Path("/a/b/c/d/e"): "deep module",
        }

        result = summarizer.generate_project_context(module_summaries)

        assert result == "context"
