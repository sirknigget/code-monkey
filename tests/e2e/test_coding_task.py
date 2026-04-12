"""E2E tests for basic coding task flows (scenarios 1 and 2).

# AC: Starting work on a new project — agent creates files via real write_file tool.
# AC: Modifying an existing project — agent reads then writes via real file tools.
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

_MAIN_PY = "# Main entry point\ndef main():\n    pass\n"
_MODULE_A = "# Submodule A\n"
_MODULE_B = "# Submodule B\n"
_MODIFIED_MAIN = "# Main entry point (modified)\ndef main():\n    import logging\n"


@pytest.mark.asyncio
async def test_new_project_agent_creates_files(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: First message → mapping → orchestrator calls write_file → file created.
    config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("main.py", _MAIN_PY),
            "App created successfully.",
        ]
    )
    ui = await run_session(
        project_dir,
        [InputEvent("create an app with two submodules and a main file")],
        db_path,
        model_config=config,
    )

    assert (project_dir / "main.py").read_text() == _MAIN_PY
    assert ui.assistant_messages() == [
        "[map_project_node] mapping skipped (no modified files)",
        "App created successfully.",
    ]


@pytest.mark.asyncio
async def test_multiple_messages_each_create_a_file(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: Two user messages — each triggers write_file for a different submodule.
    config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("submodule_a.py", _MODULE_A, call_id="c1"),
            "Submodule A created.",
            write_file_call("submodule_b.py", _MODULE_B, call_id="c2"),
            "Submodule B created.",
        ]
    )
    ui = await run_session(
        project_dir,
        [InputEvent("create submodule_a.py"), InputEvent("create submodule_b.py")],
        db_path,
        model_config=config,
    )

    assert (project_dir / "submodule_a.py").read_text() == _MODULE_A
    assert (project_dir / "submodule_b.py").read_text() == _MODULE_B
    assert ui.assistant_messages() == [
        "[map_project_node] mapping skipped (no modified files)",
        "Submodule A created.",
        "Submodule B created.",
    ]


@pytest.mark.asyncio
async def test_modify_project_reads_and_rewrites_file(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: Session 1 creates main.py; session 2 reads then rewrites it.
    session1_config = FakeModelConfig(
        orchestrator_responses=[
            write_file_call("main.py", _MAIN_PY),
            "Initial app created.",
        ]
    )
    await run_session(
        project_dir,
        [InputEvent("create the initial app")],
        db_path,
        model_config=session1_config,
    )

    session2_config = FakeModelConfig(
        orchestrator_responses=[
            read_file_call("main.py", call_id="c1"),
            write_file_call("main.py", _MODIFIED_MAIN, call_id="c2"),
            "App updated with logging.",
        ]
    )
    ui2 = await run_session(
        project_dir,
        [InputEvent("add logging to main.py")],
        db_path,
        model_config=session2_config,
    )

    assert (project_dir / "main.py").read_text() == _MODIFIED_MAIN
    assert ("system", "Resuming previous session.") in ui2.messages
    assert ui2.assistant_messages()[-1] == "App updated with logging."
