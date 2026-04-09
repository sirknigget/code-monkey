"""Unit tests for the Tester component."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from unittest.mock import MagicMock

from code_monkey.agents.tester.tester import Tester, TesterResult


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class MockBashTool(BaseTool):
    """Minimal BaseTool subclass used as a stand-in for the real bash tool."""

    name: str = "bash"
    description: str = "Run bash commands"

    def _run(self, *args, **kwargs) -> str:
        return ""

    async def _arun(self, *args, **kwargs) -> str:
        return ""


def _make_bash_call_message() -> AIMessage:
    """Return an AIMessage that contains a bash tool call."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "bash",
                "args": {"commands": "pytest"},
                "id": "call_bash",
                "type": "tool_call",
            }
        ],
    )


def _make_submit_result_message(status: str, reason: str = "") -> AIMessage:
    """Return an AIMessage that calls submit_result (the exit tool)."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "submit_result",
                "args": {"status": status, "reason": reason},
                "id": "call_submit",
                "type": "tool_call",
            }
        ],
    )


def _make_mock_model(call_responses: list[AIMessage]) -> MagicMock:
    """
    Build a mock BaseChatModel where bind_tools() returns a sub-mock whose
    ainvoke() cycles through call_responses in order.
    """
    model = MagicMock()
    bound = MagicMock()
    call_count = {"n": 0}

    async def bound_ainvoke(messages, **kwargs):
        idx = call_count["n"]
        call_count["n"] += 1
        return call_responses[idx]

    bound.ainvoke = bound_ainvoke
    model.bind_tools.return_value = bound
    return model


# ---------------------------------------------------------------------------
# Tester tests
# ---------------------------------------------------------------------------


class TestTester:
    @pytest.mark.asyncio
    async def test_passes_immediately_no_bash_calls(self) -> None:
        """Model calls submit_result immediately → passed."""
        bash_tool = MockBashTool()
        model = _make_mock_model([_make_submit_result_message("passed")])

        tester = Tester(model=model, bash_tool=bash_tool)
        result = await tester.run(project_context=None, chat_summary="", last_messages=[])

        assert result == TesterResult(status="passed", reason="")

    @pytest.mark.asyncio
    async def test_runs_bash_tool_then_passes(self) -> None:
        """Model calls bash on first turn, then submit_result(passed)."""
        bash_tool = MockBashTool()
        model = _make_mock_model([
            _make_bash_call_message(),
            _make_submit_result_message("passed", "All tests green"),
        ])

        tester = Tester(
            model=model,
            bash_tool=bash_tool,
        )
        result = await tester.run(
            project_context="A Python CLI project.",
            chat_summary="User asked to add a feature.",
            last_messages=[
                HumanMessage(content="Add a feature"),
                AIMessage(content="Done."),
            ],
        )

        assert result.status == "passed"

    @pytest.mark.asyncio
    async def test_fails_when_submit_result_is_failed(self) -> None:
        """Model calls submit_result(failed) → failed result with reason."""
        bash_tool = MockBashTool()
        model = _make_mock_model([
            _make_submit_result_message("failed", "Tests failed: 3 errors"),
        ])

        tester = Tester(model=model, bash_tool=bash_tool)
        result = await tester.run(project_context=None, chat_summary="", last_messages=[])

        assert result == TesterResult(status="failed", reason="Tests failed: 3 errors")
