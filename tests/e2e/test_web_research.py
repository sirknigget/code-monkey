"""E2E tests for web research tool-call routing (scenario 4).

# AC: Orchestrator can call web_search; the real WebResearcher executes and the
#     result is returned for the orchestrator to produce a final response.
# AC: File tools and web search can be combined in one session.
# @category: e2e
# Note: WebResearcher's fake model returns text directly so Playwright is
#       initialized but no actual network calls are made.
"""

from pathlib import Path

import pytest

from code_monkey.ui.protocol import InputEvent
from tests.e2e.conftest import (
    FakeModelConfig,
    web_search_call,
    write_file_call,
    run_session,
)


@pytest.mark.asyncio
async def test_web_search_executes_and_result_reaches_orchestrator(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: orchestrator emits web_search → WebResearcher runs (fake model) →
    #           tool result feeds back → orchestrator returns final text.
    config = FakeModelConfig(
        orchestrator_responses=[
            web_search_call("Python latest release"),
            "Research complete.",
        ]
    )
    ui = await run_session(
        project_dir,
        [InputEvent("research the latest Python release")],
        db_path,
        model_config=config,
    )

    # Only text AIMessages appear; tool call and ToolMessage are not shown.
    assert ui.assistant_messages() == [
        "[map_project_node] project mapped",
        "Research complete.",
    ]


@pytest.mark.asyncio
async def test_web_search_followed_by_write_file_in_same_session(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: First message uses web_search; second uses write_file.
    #           Both tools execute against the real ToolNode.
    config = FakeModelConfig(
        orchestrator_responses=[
            web_search_call("Python latest release", call_id="c1"),
            "Research done.",
            write_file_call("notes.py", "# research notes\n", call_id="c2"),
            "Notes saved.",
        ]
    )
    ui = await run_session(
        project_dir,
        [
            InputEvent("research Python"),
            InputEvent("save the research to notes.py"),
        ],
        db_path,
        model_config=config,
    )

    assert (project_dir / "notes.py").read_text() == "# research notes\n"
    assert ui.assistant_messages() == [
        "[map_project_node] project mapped",
        "Research done.",
        "Notes saved.",
    ]


@pytest.mark.asyncio
async def test_no_tool_call_goes_directly_to_end(
    project_dir: Path, db_path: Path
) -> None:
    # Behavior: Without a tool call the graph routes orchestrator → END, skipping tools.
    ui = await run_session(
        project_dir,
        [InputEvent("what is the capital of France")],
        db_path,
    )

    assert ui.assistant_messages() == [
        "[map_project_node] project mapped",
        "Task completed.",
    ]
