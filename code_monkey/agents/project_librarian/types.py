from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FileContext:
    """A file in the code hierarchy."""

    summary: str | None


@dataclass
class ModuleContext:
    """A module in the code hierarchy."""

    summary: str | None
    files: dict[str, FileContext] = field(default_factory=dict)
    submodules: dict[str, "ModuleContext"] = field(default_factory=dict)
