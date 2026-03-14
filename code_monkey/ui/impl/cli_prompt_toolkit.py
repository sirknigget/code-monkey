"""Terminal CLI implementation of ChatbotUI using prompt_toolkit."""

from __future__ import annotations

from io import TextIOBase
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.input import Input
from prompt_toolkit.output import Output
from prompt_toolkit.shortcuts import print_formatted_text

from code_monkey.ui.protocol import Command, InputEvent

# Map of slash-command values to Command enum members (excludes USER_INPUT).
_SLASH_COMMANDS: dict[str, Command] = {
    cmd.value: cmd for cmd in Command if cmd != Command.USER_INPUT
}


class _SlashCompleter(Completer):
    """Autocompletes "/" + command names only when input starts with "/"."""

    def get_completions(self, document: Document, complete_event):  # type: ignore[override]
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        partial = text[1:]
        for name in _SLASH_COMMANDS:
            if name.startswith(partial):
                yield Completion(f"/{name}", start_position=-len(text))


class PromptToolkitChatbotUI:
    """Terminal chat UI backed by prompt_toolkit.

    Args:
        input:   Optional prompt_toolkit Input for dependency injection (tests).
        output:  Optional prompt_toolkit Output for dependency injection (tests).
        stdout:  Optional stream for assistant_message / system_message output.
                 Defaults to sys.stdout via prompt_toolkit's auto-detection.
        stderr:  Optional stream for show_error output.
                 Defaults to sys.stderr via prompt_toolkit's auto-detection.
    """

    def __init__(
        self,
        input: Optional[Input] = None,
        output: Optional[Output] = None,
        stdout: Optional[TextIOBase] = None,
        stderr: Optional[TextIOBase] = None,
    ) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self._session: PromptSession = PromptSession(
            completer=_SlashCompleter(),
            reserve_space_for_menu=0,
            input=input,
            output=output,
        )

    # ------------------------------------------------------------------
    # ChatbotUI protocol
    # ------------------------------------------------------------------

    def get_input(self, prompt: str) -> InputEvent:
        try:
            text: str = self._session.prompt(prompt)
        except KeyboardInterrupt:
            raise SystemExit(0)
        except EOFError:
            raise SystemExit(0)

        if text.startswith("/"):
            command_name = text[1:].strip()
            command = _SLASH_COMMANDS.get(command_name, Command.USER_INPUT)
            return InputEvent(text=text, command=command)

        return InputEvent(text=text, command=Command.USER_INPUT)

    def assistant_message(self, content: str) -> None:
        print_formatted_text(
            FormattedText([("bold ansicyan", "Assistant: "), ("", content)]),
            file=self._stdout,
        )

    def system_message(self, content: str) -> None:
        print_formatted_text(
            FormattedText([("ansiyellow", "[System] "), ("", content)]),
            file=self._stdout,
        )

    def show_error(self, text: str) -> None:
        import sys

        print_formatted_text(
            FormattedText([("bold ansired", "Error: "), ("", text)]),
            file=self._stderr or sys.stderr,
        )
