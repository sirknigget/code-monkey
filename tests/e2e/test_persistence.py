"""E2E tests for filesystem persistence and per-project isolation (scenarios 7 and 8).

# AC: Conversation history and tool side-effects are stored on disk, not just in memory.
# AC: Each project directory gets a separate conversation history.
# @category: e2e
"""

from pathlib import Path

import pytest

from code_monkey.ui.protocol import InputEvent
from tests.e2e.conftest import (
    FakeModelConfig,
    read_file_call,
    run_session,
    write_file_call,
)

_CONTENT = "# module\n"


@pytest.mark.asyncio
async def test_checkpoint_and_file_are_written_to_disk(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: After a session, the SQLite checkpoint file and the tool-created
    #           file both exist on disk — proving persistence beyond memory.
    assert not db_path.exists()

    config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("module.py", _CONTENT),
            "Module created.",
        ]
    )
    await run_session(
        project_dir,
        [InputEvent("create module.py")],
        db_path,
        model_config=config,
    )

    assert db_path.exists()
    assert (project_dir / "module.py").read_text() == _CONTENT


@pytest.mark.asyncio
async def test_history_and_files_survive_process_restart(
    project_dir: Path, db_path: Path
) -> None:
    # Session 1 creates a file. Session 2 (fresh process simulation) reads it from disk.
    session1_config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("data.py", _CONTENT),
            "Data created.",
        ]
    )
    await run_session(
        project_dir,
        [InputEvent("create data.py")],
        db_path,
        model_config=session1_config,
    )

    session2_config = FakeModelConfig(
        orchestrator_responses=[
            read_file_call("data.py"),
            "Data read.",
        ]
    )
    ui2 = await run_session(
        project_dir,
        [InputEvent("read data.py")],
        db_path,
        model_config=session2_config,
    )

    assert ("system", "Resuming previous session.") in ui2.messages
    assert ui2.assistant_messages()[-1] == "Data read."


@pytest.mark.asyncio
async def test_different_projects_have_separate_histories_and_files(
    tmp_path: Path, db_path: Path
) -> None:
    # Two project directories use different thread IDs in the same SQLite DB.
    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    project_a.mkdir()
    project_b.mkdir()

    config_a = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("a_module.py", "# A\n"),
            "A module created.",
        ]
    )
    config_b = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("b_module.py", "# B\n"),
            "B module created.",
        ]
    )

    await run_session(project_a, [InputEvent("task for A")], db_path, model_config=config_a)
    await run_session(project_b, [InputEvent("task for B")], db_path, model_config=config_b)

    ui_a2 = await run_session(project_a, [], db_path)
    ui_b2 = await run_session(project_b, [], db_path)

    # Each project resumes its own session.
    assert ("system", "Resuming previous session.") in ui_a2.messages
    assert ("system", "Resuming previous session.") in ui_b2.messages

    # Histories are isolated — A's replay has A's message, not B's, and vice versa.
    assert ("user", "task for A") in ui_a2.messages
    assert ("user", "task for B") not in ui_a2.messages

    assert ("user", "task for B") in ui_b2.messages
    assert ("user", "task for A") not in ui_b2.messages

    # Files are isolated to each project directory.
    assert (project_a / "a_module.py").exists()
    assert not (project_a / "b_module.py").exists()

    assert (project_b / "b_module.py").exists()
    assert not (project_b / "a_module.py").exists()
