"""E2E tests for conversation history persistence and clearing (scenarios 5 and 6).

# AC: Conversation history (including tool-created files) is replayed on resume.
# AC: /clear command deletes the session so the next run starts fresh.
# @category: e2e
"""

from pathlib import Path

import pytest

from code_monkey.ui.protocol import Command, InputEvent
from tests.e2e.conftest import (
    FakeModelConfig,
    read_file_call,
    run_session,
    write_file_call,
)

_APP_PY = "# App module\n"


@pytest.mark.asyncio
async def test_history_is_replayed_on_session_resume(
    project_dir: Path, db_path: Path
) -> None:
    # Session 1: agent creates app.py via write_file.
    session1_config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("app.py", _APP_PY),
            "App created.",
        ]
    )
    await run_session(
        project_dir,
        [InputEvent("create app.py")],
        db_path,
        model_config=session1_config,
    )

    # Session 2: resumes and reads the file from session 1.
    session2_config = FakeModelConfig(
        orchestrator_responses=[
            read_file_call("app.py"),
            "Read app.py.",
        ]
    )
    ui2 = await run_session(
        project_dir,
        [InputEvent("read app.py")],
        db_path,
        model_config=session2_config,
    )

    assert ("system", "Resuming previous session.") in ui2.messages
    assert ui2.assistant_messages()[-1] == "Read app.py."


@pytest.mark.asyncio
async def test_replayed_history_contains_previous_tool_messages(
    project_dir: Path, db_path: Path
) -> None:
    # Session 1's user message and assistant responses should appear in session 2's replay.
    session1_config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("app.py", _APP_PY),
            "App created.",
        ]
    )
    await run_session(
        project_dir,
        [InputEvent("create app.py")],
        db_path,
        model_config=session1_config,
    )
    ui2 = await run_session(project_dir, [], db_path)

    resume_idx = next(
        i for i, m in enumerate(ui2.messages)
        if m == ("system", "Resuming previous session.")
    )
    replayed = ui2.messages[:resume_idx]
    assert ("user", "create app.py") in replayed
    assert ("assistant", "App created.") in replayed


@pytest.mark.asyncio
async def test_clear_command_resets_session(project_dir: Path, db_path: Path) -> None:
    # After /clear, next session starts fresh — no replay.
    session1_config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("app.py", _APP_PY),
            "App created.",
        ]
    )
    await run_session(
        project_dir,
        [InputEvent("create app.py"), InputEvent("/clear", Command.CLEAR)],
        db_path,
        model_config=session1_config,
    )
    ui2 = await run_session(project_dir, [], db_path)

    assert ("system", "Resuming previous session.") not in ui2.messages


@pytest.mark.asyncio
async def test_clear_shows_confirmation_and_next_session_can_write_again(
    project_dir: Path, db_path: Path
) -> None:
    # /clear shows confirmation; the follow-up session can still use tools.
    session1_config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("app.py", _APP_PY),
            "App created.",
        ]
    )
    ui1 = await run_session(
        project_dir,
        [InputEvent("create app.py"), InputEvent("/clear", Command.CLEAR)],
        db_path,
        model_config=session1_config,
    )
    assert ("system", "Session cleared.") in ui1.messages

    session2_config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("app_v2.py", "# v2\n"),
            "App v2 created.",
        ]
    )
    ui2 = await run_session(
        project_dir,
        [InputEvent("create app_v2.py")],
        db_path,
        model_config=session2_config,
    )

    assert (project_dir / "app_v2.py").exists()
    assert ui2.assistant_messages()[-1] == "App v2 created."
