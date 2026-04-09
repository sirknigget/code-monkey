"""Unit tests for the Tester component."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from unittest.mock import AsyncMock, MagicMock

from code_monkey.agents.tester.tester import TestOutput, Tester
from code_monkey.graph.state import TesterResult


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


def _make_tool_call_ai_message() -> AIMessage:
    """Return an AIMessage that contains a bash tool call."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "bash",
                "args": {"commands": "pytest"},
                "id": "call_abc",
                "type": "tool_call",
            }
        ],
    )


def _make_no_tool_call_ai_message() -> AIMessage:
    """Return an AIMessage with no tool calls."""
    return AIMessage(content="Done checking.")


def _make_mock_model(
    bind_tools_responses: list[AIMessage],
    structured_output_result: TestOutput,
) -> MagicMock:
    """
    Build a mock BaseChatModel where:
      - bind_tools() returns a sub-mock whose ainvoke() cycles through bind_tools_responses
      - with_structured_output(TestOutput) returns a runnable whose ainvoke() returns
        structured_output_result
    """
    model = MagicMock()

    bound = MagicMock()
    call_count = {"n": 0}

    async def bound_ainvoke(messages, **kwargs):
        idx = call_count["n"]
        call_count["n"] += 1
        return bind_tools_responses[idx]

    bound.ainvoke = bound_ainvoke
    model.bind_tools.return_value = bound

    structured = MagicMock()
    structured.ainvoke = AsyncMock(return_value=structured_output_result)
    model.with_structured_output.return_value = structured

    return model


# ---------------------------------------------------------------------------
# Tester tests
# ---------------------------------------------------------------------------


class TestTester:
    @pytest.mark.asyncio
    async def test_passes_immediately_no_tool_calls(self) -> None:
        """Model returns no tool call on first invocation → goes straight to structured output."""
        bash_tool = MockBashTool()
        model = _make_mock_model(
            bind_tools_responses=[_make_no_tool_call_ai_message()],
            structured_output_result=TestOutput(test_result="passed", reason=""),
        )

        tester = Tester(model=model, bash_tool=bash_tool)
        result = await tester.run(
            project_context=None,
            chat_summary="",
            last_messages=[],
        )

        assert result == TesterResult(status="passed", reason="")

    @pytest.mark.asyncio
    async def test_runs_bash_tool_then_passes(self) -> None:
        """Model issues a tool call on first turn, then no tool call → passes."""
        bash_tool = MockBashTool()
        model = _make_mock_model(
            bind_tools_responses=[
                _make_tool_call_ai_message(),
                _make_no_tool_call_ai_message(),
            ],
            structured_output_result=TestOutput(test_result="passed", reason="All tests green"),
        )

        tester = Tester(model=model, bash_tool=bash_tool)
        result = await tester.run(
            project_context="A Python CLI project.",
            chat_summary="User asked to add a feature.",
            last_messages=[
                HumanMessage(content="Add a feature"),
                AIMessage(content="Done."),
            ],
        )

        assert result["status"] == "passed"

    @pytest.mark.asyncio
    async def test_fails_when_structured_output_is_failed(self) -> None:
        """Model returns no tool call; structured output signals failure."""
        bash_tool = MockBashTool()
        model = _make_mock_model(
            bind_tools_responses=[_make_no_tool_call_ai_message()],
            structured_output_result=TestOutput(
                test_result="failed", reason="Tests failed: 3 errors"
            ),
        )

        tester = Tester(model=model, bash_tool=bash_tool)
        result = await tester.run(
            project_context=None,
            chat_summary="",
            last_messages=[],
        )

        assert result == TesterResult(status="failed", reason="Tests failed: 3 errors")
