"""E2E tests for the tester node integration (scenarios 5–8).

# AC: Orchestrator task completion is verified by the tester before the turn ends.
# AC: When tester fails, orchestrator gets another chance (up to MAX_REVIEW_CYCLES).
# AC: When MAX_REVIEW_CYCLES is exhausted, a warning surfaces as a system message.
# @category: e2e
"""

from pathlib import Path

import pytest

from code_monkey.graph.review_policy import MAX_REVIEW_CYCLES
from code_monkey.ui.protocol import InputEvent
from tests.e2e.conftest import FakeModelConfig, run_session


@pytest.mark.asyncio
async def test_tester_passes_no_warning(project_dir: Path, db_path: Path) -> None:
    # Behavior: Tester passes on first attempt — no warning in system messages.
    config = FakeModelConfig()
    ui = await run_session(
        project_dir,
        [InputEvent("do something")],
        db_path,
        model_config=config,
    )

    assert ui.assistant_messages() == [
        "[map_project_node] mapping skipped (no modified files)",
        "Task completed.",
    ]
    warning_msgs = [
        m for m in ui.system_messages() if m.startswith("Max review cycles")
    ]
    assert warning_msgs == []


@pytest.mark.asyncio
async def test_tester_fails_once_then_passes_on_retry(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: Tester fails once → orchestrator gets a retry → tester passes on second call.
    config = FakeModelConfig(
        orchestrator_responses=["First attempt.", "Second attempt."],
        tester_fails_times=1,
    )
    ui = await run_session(
        project_dir,
        [InputEvent("do something")],
        db_path,
        model_config=config,
    )

    assert ui.assistant_messages() == [
        "[map_project_node] mapping skipped (no modified files)",
        "First attempt.",
        "Second attempt.",
    ]
    warning_msgs = [
        m for m in ui.system_messages() if m.startswith("Max review cycles")
    ]
    assert warning_msgs == []


@pytest.mark.asyncio
async def test_tester_fails_max_cycles_emits_warning(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: Tester fails on every call; after MAX_REVIEW_CYCLES a warning is emitted.
    orchestrator_responses = [f"Attempt {i + 1}." for i in range(MAX_REVIEW_CYCLES)]
    config = FakeModelConfig(
        orchestrator_responses=orchestrator_responses,
        tester_fails_times=MAX_REVIEW_CYCLES,
    )
    ui = await run_session(
        project_dir,
        [InputEvent("do something")],
        db_path,
        model_config=config,
    )

    system_msgs = ui.system_messages()
    warning_msgs = [m for m in system_msgs if m.startswith("Max review cycles")]
    assert len(warning_msgs) == 1

    assistant_msgs = ui.assistant_messages()
    for msg in assistant_msgs:
        assert not msg.startswith("Max review cycles")


@pytest.mark.asyncio
async def test_no_tool_call_routes_through_tester_to_end(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: Without tool calls, graph routes orchestrator → summarizer → tester → END.
    #           The final assistant message is the orchestrator's only response.
    ui = await run_session(
        project_dir,
        [InputEvent("what is the capital of France")],
        db_path,
    )

    assert ui.assistant_messages() == [
        "[map_project_node] mapping skipped (no modified files)",
        "Task completed.",
    ]
