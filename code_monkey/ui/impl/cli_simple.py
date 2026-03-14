"""Terminal CLI implementation of ChatbotUI using Python builtins."""

from __future__ import annotations

import sys
from io import TextIOBase
from typing import Optional

from code_monkey.ui.protocol import Command, InputEvent

# ANSI color/style codes
_RESET = "\033[0m"
_BOLD = "\033[1m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_RED = "\033[31m"

# Map of slash-command values to Command enum members (excludes USER_INPUT).
_SLASH_COMMANDS: dict[str, Command] = {
    cmd.value: cmd for cmd in Command if cmd != Command.USER_INPUT
}


class SimpleCliChatbotUI:
    """Terminal chat UI backed by Python builtins with ANSI color support.

    Args:
        stdin:  Optional input stream. Defaults to sys.stdin.
        stdout: Optional output stream for assistant/system messages. Defaults to sys.stdout.
        stderr: Optional output stream for error messages. Defaults to sys.stderr.
    """

    def __init__(
        self,
        stdin: Optional[TextIOBase] = None,
        stdout: Optional[TextIOBase] = None,
        stderr: Optional[TextIOBase] = None,
    ) -> None:
        self._stdin = stdin or sys.stdin
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    # ------------------------------------------------------------------
    # ChatbotUI protocol
    # ------------------------------------------------------------------

    def get_input(self, prompt: str) -> InputEvent:
        try:
            self._stdout.write(prompt)
            self._stdout.flush()
            text = self._stdin.readline()
        except KeyboardInterrupt:
            raise SystemExit(0)
        except EOFError:
            raise SystemExit(0)

        if not text:  # empty readline means EOF
            raise SystemExit(0)

        text = text.rstrip("\r\n")

        if text.startswith("/"):
            command_name = text[1:].strip()
            command = _SLASH_COMMANDS.get(command_name, Command.USER_INPUT)
            return InputEvent(text=text, command=command)

        return InputEvent(text=text, command=Command.USER_INPUT)

    def assistant_message(self, content: str) -> None:
        self._stdout.write(f"{_BOLD}{_CYAN}Assistant: {_RESET}{content}\n")
        self._stdout.flush()

    def system_message(self, content: str) -> None:
        self._stdout.write(f"{_YELLOW}[System] {_RESET}{content}\n")
        self._stdout.flush()

    def show_error(self, text: str) -> None:
        self._stderr.write(f"{_BOLD}{_RED}Error: {_RESET}{text}\n")
        self._stderr.flush()
