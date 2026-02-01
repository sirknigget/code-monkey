"""LLM-based summarizer with retry logic."""

import time
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence


class Summarizer:
    """LLM-based file, module, and project summarization with retry logic.

    Uses three distinct prompt templates for different summarization levels.
    Implements exponential backoff retry for LLM failures.
    """

    MAX_SUMMARY_LINES = 10
    MAX_RETRIES = 3
    BACKOFF_BASE = 2.0
    INITIAL_DELAY = 1.0

    def __init__(self, llm: BaseChatModel) -> None:
        """Initialize summarizer with LLM.

        Args:
            llm: LangChain BaseChatModel instance.
        """
        self.llm = llm
        self._file_chain = self._create_file_summary_chain()
        self._module_chain = self._create_module_summary_chain()
        self._project_chain = self._create_project_summary_chain()

    def _create_file_summary_chain(self) -> RunnableSequence:
        """Create LangChain chain for file summaries.

        Returns:
            RunnableSequence for file summarization.
        """
        template = """You are a code analyst. Summarize this Python file concisely.

File: {filepath}
Structure:
{structure}

Parent module context (if any):
{parent_context}

Requirements:
- 2-3 sentences maximum
- State the file's primary purpose
- Mention key classes and functions
- Use active voice
- Keep under {max_lines} lines

Summary:"""
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def _create_module_summary_chain(self) -> RunnableSequence:
        """Create LangChain chain for module summaries.

        Returns:
            RunnableSequence for module summarization.
        """
        template = """You are a code analyst. Summarize this Python module (directory).

Module: {module_path}

File summaries:
{file_summaries}

Parent module context (if any):
{parent_context}

Requirements:
- 3-5 sentences maximum
- Describe the module's purpose and what it provides
- Explain relationships between files
- Mention key exports/APIs
- Keep under {max_lines} lines

Summary:"""
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def _create_project_summary_chain(self) -> RunnableSequence:
        """Create LangChain chain for project context.

        Returns:
            RunnableSequence for project context generation.
        """
        template = """You are a code analyst. Create a project structure overview.

Module summaries by directory:
{module_summaries}

Requirements:
- Use indentation tree format to show directory hierarchy
- Show module purpose at each level
- Maximum 10 lines total
- Focus on key modules and their responsibilities

Project Structure:
```
{project_name}
{indented_summary}
```"""
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def _summarize_with_retry(
        self, chain: RunnableSequence, input: dict, max_lines: int
    ) -> str:
        """Execute summarization with exponential backoff retry.

        Args:
            chain: LangChain chain to execute.
            input: Dictionary of template variables.
            max_lines: Maximum allowed lines in output.

        Returns:
            Summary string (truncated to max_lines if needed).

        Raises:
            RuntimeError: After all retries are exhausted.
        """
        last_error: Exception | None = None
        delay = self.INITIAL_DELAY

        for attempt in range(self.MAX_RETRIES):
            try:
                result = chain.invoke(input).strip()
                # Truncate to max_lines
                lines = result.split("\n")
                if len(lines) > max_lines:
                    result = "\n".join(lines[:max_lines])
                return result
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= self.BACKOFF_BASE

        raise RuntimeError(
            f"Summarization failed after {self.MAX_RETRIES} attempts: {last_error}"
        )

    def summarize_file(
        self,
        filepath: Path,
        structure: str,
        parent_context: str | None = None,
    ) -> str:
        """Generate summary for a single file.

        Args:
            filepath: Path to the file.
            structure: Parsed code structure string.
            parent_context: Optional parent module context.

        Returns:
            File summary string.
        """
        input_vars = {
            "filepath": str(filepath),
            "structure": structure,
            "parent_context": parent_context or "(none)",
            "max_lines": self.MAX_SUMMARY_LINES,
        }
        return self._summarize_with_retry(
            self._file_chain, input_vars, self.MAX_SUMMARY_LINES
        )

    def summarize_module(
        self,
        directory: Path,
        file_summaries: list[str],
        parent_context: str | None = None,
    ) -> str:
        """Generate summary for a module (directory).

        Args:
            directory: Path to the module directory.
            file_summaries: List of file summary strings.
            parent_context: Optional parent module context.

        Returns:
            Module summary string.
        """
        combined_summaries = "\n---\n".join(file_summaries)
        input_vars = {
            "module_path": str(directory),
            "file_summaries": combined_summaries,
            "parent_context": parent_context or "(none)",
            "max_lines": self.MAX_SUMMARY_LINES,
        }
        return self._summarize_with_retry(
            self._module_chain, input_vars, self.MAX_SUMMARY_LINES
        )

    def generate_project_context(
        self, module_summaries: dict[Path, str], project_name: str = "project"
    ) -> str:
        """Generate project-wide context using indentation tree format.

        Args:
            module_summaries: Dictionary mapping directory paths to summaries.
            project_name: Name of the project for display.

        Returns:
            Project context string in indentation tree format.
        """
        # Format module summaries for the template
        summary_parts = []
        for dir_path, summary in sorted(module_summaries.items()):
            rel_path = dir_path.relative_to(dir_path.root)
            summary_parts.append(f"{rel_path}: {summary}")

        combined = "\n".join(summary_parts)

        input_vars = {
            "module_summaries": combined,
            "project_name": project_name,
            "indented_summary": combined,  # Will be indented by template
        }
        return self._summarize_with_retry(
            self._project_chain, input_vars, self.MAX_SUMMARY_LINES
        )


__all__ = ["Summarizer"]
