"""E2E tests for project mapping sanity (scenario 3).

# AC: Project mapping runs on the first turn of a new session.
# AC: Mapping does not re-run on subsequent turns unless explicitly requested.
# AC: /map command schedules re-mapping for the next message.
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

_HELLO_PY = "def hello():\n    return 'hello'\n"


@pytest.mark.asyncio
async def test_mapping_runs_before_first_orchestrator_call(
    project_dir: Path, db_path: Path
) -> None:
    # Pre-create a Python file so the mapper has something to process.
    (project_dir / "hello.py").write_text(_HELLO_PY)

    config = FakeModelConfig(
        orchestrator_responses=[
            read_file_call("hello.py"),
            "Read hello.py successfully.",
        ]
    )
    ui = await run_session(
        project_dir,
        [InputEvent("read hello.py")],
        db_path,
        model_config=config,
    )

    # Mapping message appears before the orchestrator's final response.
    assert ui.assistant_messages() == [
        "[map_project_node] project mapped",
        "Read hello.py successfully.",
    ]


@pytest.mark.asyncio
async def test_mapping_does_not_repeat_within_same_session(
    project_dir: Path, db_path: Path
) -> None:
    # Second message in the same session skips mapping (needs_mapping=False).
    config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("a.py", "# a\n", call_id="c1"),
            "Created a.py.",
            write_file_call("b.py", "# b\n", call_id="c2"),
            "Created b.py.",
        ]
    )
    ui = await run_session(
        project_dir,
        [InputEvent("create a.py"), InputEvent("create b.py")],
        db_path,
        model_config=config,
    )

    assert ui.assistant_messages() == [
        "[map_project_node] project mapped",
        "Created a.py.",
        "Created b.py.",
    ]


@pytest.mark.asyncio
async def test_map_command_triggers_remapping_on_next_message(
    project_dir: Path, db_path: Path
) -> None:
    # /map sets needs_mapping=True; the map node fires again on the next message.
    config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("first.py", "# first\n", call_id="c1"),
            "Created first.py.",
            write_file_call("second.py", "# second\n", call_id="c2"),
            "Created second.py.",
        ]
    )
    ui = await run_session(
        project_dir,
        [
            InputEvent("create first.py"),
            InputEvent("/map", Command.MAP),
            InputEvent("create second.py"),
        ],
        db_path,
        model_config=config,
    )

    assert ui.assistant_messages() == [
        "[map_project_node] project mapped",
        "Created first.py.",
        "[map_project_node] project mapped",
        "Created second.py.",
    ]
    assert (project_dir / "first.py").exists()
    assert (project_dir / "second.py").exists()
