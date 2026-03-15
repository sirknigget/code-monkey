"""Tests for SimpleCliChatbotUI.

All four protocol methods are exercised through the real implementation.
I/O is injected via io.StringIO — no subprocess or real TTY involved.
"""

import io

import pytest

from code_monkey.ui.impl.cli_simple import (
    SimpleCliChatbotUI,
    _BOLD,
    _CYAN,
    _GREEN,
    _RED,
    _RESET,
    _YELLOW,
)
from code_monkey.ui.protocol import Command, InputEvent


def _make_ui(
    stdin_text: str = "",
    stdout: io.StringIO | None = None,
    stderr: io.StringIO | None = None,
) -> SimpleCliChatbotUI:
    return SimpleCliChatbotUI(
        stdin=io.StringIO(stdin_text),
        stdout=stdout or io.StringIO(),
        stderr=stderr or io.StringIO(),
    )


# ---------------------------------------------------------------------------
# get_input — plain text
# ---------------------------------------------------------------------------


def test_get_input_plain_text_returns_user_input_command():
    result = _make_ui("hello\n").get_input("> ")
    assert result == InputEvent(text="hello", command=Command.USER_INPUT)


def test_get_input_empty_text_returns_user_input_command():
    result = _make_ui("\n").get_input("> ")
    assert result == InputEvent(text="", command=Command.USER_INPUT)


# ---------------------------------------------------------------------------
# get_input — slash commands
# ---------------------------------------------------------------------------


def test_get_input_slash_clear_returns_clear_command():
    result = _make_ui("/clear\n").get_input("> ")
    assert result == InputEvent(text="/clear", command=Command.CLEAR)


def test_get_input_unknown_slash_command_falls_back_to_user_input():
    result = _make_ui("/unknown\n").get_input("> ")
    assert result == InputEvent(text="/unknown", command=Command.USER_INPUT)


# ---------------------------------------------------------------------------
# get_input — exit signals
# ---------------------------------------------------------------------------


def test_eof_raises_system_exit():
    with pytest.raises(SystemExit):
        _make_ui("").get_input("> ")


def test_ctrl_c_raises_system_exit():
    class _InterruptStream:
        def readline(self) -> str:
            raise KeyboardInterrupt

        def write(self, _: str) -> None:
            pass

        def flush(self) -> None:
            pass

    ui = SimpleCliChatbotUI(
        stdin=_InterruptStream(), stdout=io.StringIO(), stderr=io.StringIO()
    )  # type: ignore[arg-type]
    with pytest.raises(SystemExit):
        ui.get_input("> ")


# ---------------------------------------------------------------------------
# Output methods
# ---------------------------------------------------------------------------


def test_user_message_writes_to_stdout():
    out = io.StringIO()
    _make_ui(stdout=out).user_message("Hello!")
    assert out.getvalue() == f"{_BOLD}{_GREEN}You: {_RESET}Hello!\n"


def test_assistant_message_writes_to_stdout():
    out = io.StringIO()
    _make_ui(stdout=out).assistant_message("Hello there!")
    assert out.getvalue() == f"{_BOLD}{_CYAN}Assistant: {_RESET}Hello there!\n"


def test_system_message_writes_to_stdout():
    out = io.StringIO()
    _make_ui(stdout=out).system_message("Starting up...")
    assert out.getvalue() == f"{_YELLOW}[System] {_RESET}Starting up...\n"


def test_show_error_writes_to_stdout():
    out = io.StringIO()
    _make_ui(stdout=out).show_error("Something went wrong")
    assert out.getvalue() == f"{_BOLD}{_RED}Error: {_RESET}Something went wrong\n"
