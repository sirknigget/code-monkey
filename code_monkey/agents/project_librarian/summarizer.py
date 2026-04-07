"""LLM-based summarizer with LangChain retry."""

import time
from pathlib import Path
from typing import NamedTuple

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

from code_monkey.agents.project_librarian.summarizer_prompts import (
    FILE_SUMMARY_TEMPLATE,
    MODULE_SUMMARY_TEMPLATE,
    PROJECT_SUMMARY_TEMPLATE,
)
from code_monkey.agents.project_librarian.types import ModuleContext
from code_monkey.utils.log_utils import get_formatted_logger

logger = get_formatted_logger(__name__)


class Summarizer:
    """LLM-based file, module, and project summarization.

    Uses three distinct prompt templates for different summarization levels.
    Relies on LangChain's built-in retry support on the LLM.
    """

    MAX_FILE_SUMMARY_LINES = 20
    MAX_MODULE_SUMMARY_LINES = 100
    MAX_PROJECT_SUMMARY_LINES = 1000
    MAX_RETRIES = 3

    def __init__(self, llm: BaseChatModel, working_dir: Path) -> None:
        """Initialize summarizer with LLM.

        Args:
            llm: LangChain BaseChatModel instance.
            working_dir: Project root; paths sent to the LLM are relative to this.
        """
        # Attach retry behavior directly to the LLM runnable.
        self.llm = llm.with_retry(stop_after_attempt=self.MAX_RETRIES)
        self._working_dir = working_dir

        self._file_chain = self._create_file_summary_chain()
        self._module_chain = self._create_module_summary_chain()
        self._project_chain = self._create_project_summary_chain()

    def _rel(self, path: Path) -> Path:
        try:
            return path.relative_to(self._working_dir)
        except ValueError:
            return path

    def _create_file_summary_chain(self) -> RunnableSerializable:
        """Create LangChain chain for file summaries.

        Returns:
            RunnableSerializable for file summarization.
        """
        template = FILE_SUMMARY_TEMPLATE
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def _create_module_summary_chain(self) -> RunnableSerializable:
        """Create LangChain chain for module summaries.

        Returns:
            RunnableSerializable for module summarization.
        """
        template = MODULE_SUMMARY_TEMPLATE
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def _create_project_summary_chain(self) -> RunnableSerializable:
        """Create LangChain chain for project context.

        Returns:
            RunnableSerializable for project context generation.
        """
        template = PROJECT_SUMMARY_TEMPLATE
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def summarize_file(
        self,
        filepath: Path,
        code: str,
    ) -> str:
        """Generate summary for a single file.

        Args:
            filepath: Path to the file.
            code: code string.

        Returns:
            File summary string.
        """
        logger.debug("Summarizing file: %s", self._rel(filepath))
        input_vars = {
            "filepath": str(self._rel(filepath)),
            "code": code,
            "max_lines": self.MAX_FILE_SUMMARY_LINES,
        }
        start = time.perf_counter()
        result = self._file_chain.invoke(input_vars).strip()
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug("File summarized: %s (%.0f ms)", self._rel(filepath), elapsed_ms)
        return result

    class FileInfo(NamedTuple):
        filepath: Path
        summary: str

    @staticmethod
    def _format_file_info(info: "Summarizer.FileInfo") -> str:
        return f"File: {info.filepath.name} -> Summary:\n{info.summary}"

    def summarize_module(
        self,
        directory: Path,
        file_infos: list[FileInfo],
        submodule_infos: list[FileInfo],
        parent_context: str | None = None,
    ) -> str:
        """Generate summary for a module (directory).

        Args:
            directory: Path to the module directory.
            file_infos: List of FileInfo tuples for files in the module.
            submodule_infos: List of FileInfo tuples for submodules.
            parent_context: Optional parent module context.

        Returns:
            Module summary string.
        """
        logger.debug(
            "Summarizing module: %s (%d file(s), %d submodule(s))",
            self._rel(directory),
            len(file_infos),
            len(submodule_infos),
        )
        combined_file_summaries = "\n---\n".join(
            Summarizer._format_file_info(info) for info in file_infos
        )
        combined_submodule_summaries = "\n---\n".join(
            Summarizer._format_file_info(info) for info in submodule_infos
        )
        input_vars = {
            "module_path": str(self._rel(directory)),
            "file_summaries": combined_file_summaries,
            "submodule_summaries": combined_submodule_summaries,
            "parent_context": parent_context or "(none)",
            "max_lines": self.MAX_MODULE_SUMMARY_LINES,
        }
        start = time.perf_counter()
        result = self._module_chain.invoke(input_vars).strip()
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            "Module summarized: %s (%.0f ms)", self._rel(directory), elapsed_ms
        )
        return result

    def _module_summaries_from_code_context(
        self,
        code_context: ModuleContext,
    ) -> list[tuple[str, str]]:
        """Extract module summaries from code context.

        Args:
            code_context: Hierarchical code context.

        Returns:
            List of (module_path, summary) tuples.
            The root module uses an empty string as its path.
        """
        summary_parts: list[tuple[str, str]] = []

        def collect_summaries(
            module: ModuleContext,
            path: str,
        ) -> None:
            if module.summary is not None:
                summary_parts.append((path, module.summary))

            for name, submodule in module.submodules.items():
                next_path = f"{path}/{name}" if path else name
                collect_summaries(submodule, next_path)

        collect_summaries(code_context, "")
        return summary_parts

    def summarize_project(
        self,
        project_structure: str,
        code_context: ModuleContext,
        project_name: str,
    ) -> str:
        """Generate root summary from code context.

        Args:
            project_structure: Indented project structure string.
            code_context: Hierarchical code context.
            project_name: Name of the project for display.

        Returns:
            Root module summary string.
        """
        logger.debug("Summarizing project: %s", project_name)
        # Collect all module summaries recursively
        summary_parts = self._module_summaries_from_code_context(code_context)

        # Format for LLM
        formatted = []
        for path, summary in summary_parts:
            formatted.append(f"{path}:\n{summary}\n\n")

        input_vars = {
            "module_summaries": formatted,
            "project_name": project_name,
            "project_structure": project_structure,
            "max_lines": self.MAX_PROJECT_SUMMARY_LINES,
        }
        start = time.perf_counter()
        result = self._project_chain.invoke(input_vars).strip()
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug("Project summarized: %s (%.0f ms)", project_name, elapsed_ms)
        return result


__all__ = ["Summarizer"]
