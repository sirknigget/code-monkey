"""ChatbotUI protocol and related types.

The UI layer knows nothing about graphs, interrupts, or conversation roles.
It is a generic display and input surface; the controller holds all semantic
knowledge and decides what to render and when.
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple, Protocol


class Command(Enum):
    """Known UI commands surfaced by ChatbotUI.get_input().

    The UI produces a Command value; the controller interprets it.
    New commands can be added here as the UI grows.
    """

    USER_INPUT = "user_input"  # Default for plain text input.
    CLEAR = "clear"
    MAP = "map"
    EXIT = "exit"


class InputEvent(NamedTuple):
    """Immutable value object returned by ChatbotUI.get_input().

    Attributes:
        text: The raw text submitted by the user. May be empty.
        command: The user's intent. Defaults to Command.USER_INPUT for plain
            text. The controller (not the UI) interprets non-default commands.
        files: Optional file paths attached or referenced by the user.
    """

    text: str
    command: Command = Command.USER_INPUT
    files: tuple[str, ...] = ()


class ChatbotUI(Protocol):
    """Generic display and input interface for any rendering backend.

    Implementations may use a terminal, a TUI framework, a web socket, or a
    test harness — none of that is visible to the controller. All values
    crossing this boundary are plain Python primitives.
    """

    def get_input(self, prompt: str) -> InputEvent:
        """Display prompt and block until the user submits input.

        Args:
            prompt: Text to show before the input cursor.

        Returns:
            An InputEvent. text may be empty; command defaults to USER_INPUT.

        Raises:
            SystemExit: user signalled quit (e.g. Ctrl+C, Ctrl+D, window close).
        """
        ...

    def user_message(self, content: str) -> None:
        """Render a message produced by the user (e.g. during history replay)."""
        ...

    def assistant_message(self, content: str) -> None:
        """Render a message produced by the AI assistant."""
        ...

    def system_message(self, content: str) -> None:
        """Render an informational message from the system (status, hints, etc.)."""
        ...

    def show_error(self, text: str) -> None:
        """Render an error message."""
        ...
