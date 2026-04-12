"""E2E tests for the bash (terminal) tool.

# AC: Orchestrator can run shell commands; output is captured and fed back.
# AC: Bash tool requires human approval before executing (ask_human_input=True).
# @category: e2e
# Note: ShellTool calls builtins.input() for approval before each command.
#       Tests patch it to return "y" so commands execute without blocking.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage

from code_monkey.ui.protocol import InputEvent
from tests.e2e.conftest import (
    FakeModelConfig,
    run_session,
    write_file_call,
)


def terminal_call(command: str, call_id: str = "c1") -> AIMessage:
    """AIMessage that triggers a real terminal tool call."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "terminal",
                "args": {"commands": command},
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


@pytest.mark.asyncio
async def test_bash_runs_python_and_writes_output_file(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: terminal tool runs python which writes a file; we assert on the file
    #           to prove the command actually executed (not just that the LLM responded).
    config = FakeModelConfig(
        orchestrator_responses=[
            terminal_call(
                "python -c \"open('output.txt', 'w').write('hello from bash')\""
            ),
            "Script ran successfully.",
        ]
    )
    with patch("builtins.input", return_value="y"):
        ui = await run_session(
            project_dir,
            [InputEvent("run a quick python command")],
            db_path,
            model_config=config,
        )

    assert (project_dir / "output.txt").read_text() == "hello from bash"
    assert ui.assistant_messages() == [
        "[map_project_node] mapping skipped (no modified files)",
        "Script ran successfully.",
    ]


@pytest.mark.asyncio
async def test_write_file_then_run_it_with_bash(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: First message writes a Python script; second runs it with bash.
    #           The script writes a result file, proving both tools executed in order.
    _script = "open('result.txt', 'w').write('app ran')\n"
    config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("app.py", _script, call_id="c1"),
            "Script created.",
            terminal_call("python app.py", call_id="c2"),
            "Script executed.",
        ]
    )
    with patch("builtins.input", return_value="y"):
        ui = await run_session(
            project_dir,
            [InputEvent("create app.py"), InputEvent("run app.py")],
            db_path,
            model_config=config,
        )

    assert (project_dir / "app.py").read_text() == _script
    assert (project_dir / "result.txt").read_text() == "app ran"
    assert ui.assistant_messages() == [
        "[map_project_node] mapping skipped (no modified files)",
        "Script created.",
        "Script executed.",
    ]


@pytest.mark.asyncio
async def test_bash_approval_denied_does_not_execute_command(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: When the user denies approval (input returns "n"), the command is
    #           aborted and no side effects occur — file must not be created.
    config = FakeModelConfig(
        orchestrator_responses=[
            terminal_call(
                "python -c \"open('should_not_exist.txt', 'w').write('oops')\""
            ),
            "Command aborted.",
        ]
    )
    with patch("builtins.input", return_value="n"):
        ui = await run_session(
            project_dir,
            [InputEvent("run a dangerous command")],
            db_path,
            model_config=config,
        )

    assert not (project_dir / "should_not_exist.txt").exists()
    assert ui.assistant_messages()[-1] == "Command aborted."
