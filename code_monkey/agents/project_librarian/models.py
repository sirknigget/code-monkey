"""NamedTuple models for project mapping."""

from pathlib import Path
from typing import NamedTuple


class FileSummary(NamedTuple):
    """Summary of a single Python file.

    Attributes:
        filepath: Absolute path to the file.
        summary: LLM-generated summary of the file's purpose and contents.
    """

    filepath: Path
    summary: str


class ModuleSummary(NamedTuple):
    """Summary of a Python module (directory).

    Attributes:
        directory: Absolute path to the module directory.
        files: List of file summaries in this module.
        module_summary: LLM-generated summary of the module.
        parent_summary: Summary from parent module context (if any).
    """

    directory: Path
    files: list[FileSummary]
    module_summary: str
    parent_summary: str | None = None


__all__ = ["FileSummary", "ModuleSummary"]
