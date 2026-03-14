"""Integration tests for CliChatbotUI.

All four protocol methods are exercised through the real implementation.
Terminal I/O is mocked at the prompt_toolkit boundary using its injectable
input/output streams — no subprocess or real TTY involved.
"""

import io

import pytest
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from code_monkey.ui.impl.cli_prompt_toolkit import PromptToolkitChatbotUI
from code_monkey.ui.protocol import Command, InputEvent


def _make_ui(inp, stdout=None, stderr=None) -> PromptToolkitChatbotUI:
    return PromptToolkitChatbotUI(
        input=inp,
        output=DummyOutput(),
        stdout=stdout,
        stderr=stderr,
    )


# ---------------------------------------------------------------------------
# get_input — plain text
# ---------------------------------------------------------------------------


def test_get_input_plain_text_returns_user_input_command():
    with create_pipe_input() as inp:
        inp.send_text("hello\n")
        result = _make_ui(inp).get_input("> ")
    assert result == InputEvent(text="hello", command=Command.USER_INPUT)


def test_get_input_empty_text_returns_user_input_command():
    with create_pipe_input() as inp:
        inp.send_text("\n")
        result = _make_ui(inp).get_input("> ")
    assert result == InputEvent(text="", command=Command.USER_INPUT)


# ---------------------------------------------------------------------------
# get_input — slash commands
# ---------------------------------------------------------------------------


def test_get_input_slash_clear_returns_clear_command():
    with create_pipe_input() as inp:
        inp.send_text("/clear\n")
        result = _make_ui(inp).get_input("> ")
    assert result == InputEvent(text="/clear", command=Command.CLEAR)


def test_get_input_unknown_slash_command_falls_back_to_user_input():
    with create_pipe_input() as inp:
        inp.send_text("/unknown\n")
        result = _make_ui(inp).get_input("> ")
    assert result == InputEvent(text="/unknown", command=Command.USER_INPUT)


# ---------------------------------------------------------------------------
# get_input — exit signals
# ---------------------------------------------------------------------------


def test_ctrl_c_raises_system_exit():
    with create_pipe_input() as inp:
        inp.send_text("\x03")
        with pytest.raises(SystemExit):
            _make_ui(inp).get_input("> ")


def test_ctrl_d_raises_system_exit():
    with create_pipe_input() as inp:
        inp.send_text("\x04")
        with pytest.raises(SystemExit):
            _make_ui(inp).get_input("> ")


# ---------------------------------------------------------------------------
# Output methods — inject io.StringIO() to avoid pytest capsys / CRLF issues
# ---------------------------------------------------------------------------


def test_assistant_message_writes_to_stdout():
    out = io.StringIO()
    with create_pipe_input() as inp:
        _make_ui(inp, stdout=out).assistant_message("Hello there!")
    assert out.getvalue() == "Assistant: Hello there!\r\n"


def test_system_message_writes_to_stdout():
    out = io.StringIO()
    with create_pipe_input() as inp:
        _make_ui(inp, stdout=out).system_message("Starting up...")
    assert out.getvalue() == "[System] Starting up...\r\n"


def test_show_error_writes_to_stderr():
    err = io.StringIO()
    with create_pipe_input() as inp:
        _make_ui(inp, stderr=err).show_error("Something went wrong")
    assert err.getvalue() == "Error: Something went wrong\r\n"
