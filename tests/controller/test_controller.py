"""End-to-end tests for the Controller CLI loop using pexpect."""

import re
import sys
from pathlib import Path

import pexpect
import pytest


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[mGKHFl?]", "", text)


def _spawn(tmp_path: Path, project_root: Path) -> pexpect.spawn:
    """Spawn the main entry point with an isolated checkpoint DB."""
    env = {
        "CODEMONKEY_DB_PATH": str(tmp_path / "checkpoints.db"),
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(Path.home()),
        "PYTHONPATH": str(project_root),
    }
    child = pexpect.spawn(
        f"{sys.executable} -m code_monkey.main",
        cwd=str(project_root),
        env=env,
        encoding="utf-8",
        timeout=15,
    )
    return child


@pytest.fixture
def child(tmp_path, pytestconfig):
    proc = _spawn(tmp_path, pytestconfig.rootpath)
    yield proc
    if proc.isalive():
        proc.close(force=True)


def test_user_input_produces_assistant_response(child):
    # prompt_toolkit renders "You: " with cursor-positioning escapes;
    # match on "You:" (no trailing space) which appears literally in the stream.
    child.expect("You:")
    child.sendline("hello")
    child.expect("Assistant: ")
    output = _strip_ansi(child.before + child.after)
    assert "Assistant: " in output


def test_assistant_message_contains_orchestrator_content(child):
    child.expect("You:")
    child.sendline("hello")
    # First invocation triggers map_project_node, then orchestrator_node.
    # Both emit assistant messages; wait past the first to assert the second.
    child.expect("Assistant: ")
    child.expect("\r\n")  # skip map_project_node message
    child.expect("Assistant: ")
    child.expect("\r\n")
    content = _strip_ansi(child.before).rstrip("\r")
    assert content == "[orchestrator_node] ready"


def test_empty_input_reprompts_without_invoking_graph(child):
    child.expect("You:")
    child.sendline("")
    child.expect("You:")
    output = _strip_ansi(child.before)
    assert "Assistant:" not in output


def test_ctrl_d_exits_cleanly(child):
    child.expect("You:")
    child.sendcontrol("d")
    child.expect(pexpect.EOF)
    assert not child.isalive()


def test_clear_shows_session_cleared_message(child):
    child.expect("You:")
    child.sendline("/clear")
    child.expect("Session cleared.")


def test_clear_then_message_still_produces_response(child):
    child.expect("You:")
    child.sendline("/clear")
    child.expect("Session cleared.")
    child.expect("You:")
    child.sendline("hello")
    # After /clear the session is fresh, so map_project_node runs first.
    child.expect("Assistant: ")
    child.expect("\r\n")  # skip map_project_node message
    child.expect("Assistant: ")
    child.expect("\r\n")
    content = _strip_ansi(child.before).rstrip("\r")
    assert content == "[orchestrator_node] ready"


def test_session_persists_across_restart(tmp_path, pytestconfig):
    # First process: send a message so a checkpoint is created.
    proc1 = _spawn(tmp_path, pytestconfig.rootpath)
    proc1.expect("You:")
    proc1.sendline("hello")
    proc1.expect("Assistant: ")
    proc1.sendcontrol("d")
    proc1.expect(pexpect.EOF)

    # Second process: checkpoint exists → "Resuming previous session." before prompt.
    proc2 = _spawn(tmp_path, pytestconfig.rootpath)
    proc2.expect("Resuming previous session.")
    proc2.expect("You:")
    proc2.close(force=True)


def test_clear_then_restart_starts_fresh(tmp_path, pytestconfig):
    # First process: send a message then clear.
    proc1 = _spawn(tmp_path, pytestconfig.rootpath)
    proc1.expect("You:")
    proc1.sendline("hello")
    proc1.expect("Assistant: ")
    proc1.expect("You:")
    proc1.sendline("/clear")
    proc1.expect("Session cleared.")
    proc1.sendcontrol("d")
    proc1.expect(pexpect.EOF)

    # Second process: checkpoint was deleted → no "Resuming" message, prompt appears directly.
    proc2 = _spawn(tmp_path, pytestconfig.rootpath)
    proc2.expect("You:")
    output = _strip_ansi(proc2.before)
    assert "Resuming" not in output
    proc2.close(force=True)
