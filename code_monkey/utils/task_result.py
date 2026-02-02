"""Generic class for holding progress and result values."""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class TaskResult(Generic[T]):
    """Generic container for task result with progress tracking.

    Attributes:
        result: The primary result of the task.
        progress: Current progress value (0-based).
        progress_max: Maximum progress value for percentage calculation.
    """

    result: T
    progress: int
    progress_max: int

    @property
    def progress_percent(self) -> float:
        """Return progress as a percentage of max."""
        if self.progress_max == 0:
            return 0.0
        return (self.progress / self.progress_max) * 100

    def __iter__(self):
        """Allow unpacking as (result, progress, progress_max)."""
        return iter((self.result, self.progress, self.progress_max))


__all__ = ["TaskResult"]
