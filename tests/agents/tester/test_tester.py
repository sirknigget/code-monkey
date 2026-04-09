"""Unit tests for the Tester component."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool

from code_monkey.agents.tester.tester import Tester, TesterResult


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class MockBashTool(BaseTool):
    name: str = "bash"
    description: str = "Run bash commands"

    def _run(self, *args, **kwargs) -> str:
        return ""

    async def _arun(self, *args, **kwargs) -> str:
        return ""


def _make_tester(result: TesterResult) -> Tester:
    """Build a Tester whose internal agent immediately returns the given result."""
    model = MagicMock()
    bash_tool = MockBashTool()
    tester = Tester(model=model, bash_tool=bash_tool)
    tester._agent = AsyncMock()
    tester._agent.ainvoke = AsyncMock(return_value={"structured_response": result})
    return tester


# ---------------------------------------------------------------------------
# Tester tests
# ---------------------------------------------------------------------------


class TestTester:
    @pytest.mark.asyncio
    async def test_passes_returns_passed_result(self) -> None:
        tester = _make_tester(TesterResult(status="passed", reason=""))
        result = await tester.run(project_context=None, chat_summary="", last_messages=[])
        assert result == TesterResult(status="passed", reason="")

    @pytest.mark.asyncio
    async def test_fails_returns_failed_result_with_reason(self) -> None:
        tester = _make_tester(TesterResult(status="failed", reason="3 tests failed"))
        result = await tester.run(project_context=None, chat_summary="", last_messages=[])
        assert result == TesterResult(status="failed", reason="3 tests failed")

    @pytest.mark.asyncio
    async def test_context_included_in_agent_invocation(self) -> None:
        tester = _make_tester(TesterResult(status="passed", reason=""))
        await tester.run(
            project_context="A Python CLI project.",
            chat_summary="User asked to add a feature.",
            last_messages=[
                HumanMessage(content="Add a feature"),
                AIMessage(content="Done."),
            ],
        )
        call_args = tester._agent.ainvoke.call_args
        message_content = call_args[0][0]["messages"][0].content
        assert "A Python CLI project." in message_content
        assert "User asked to add a feature." in message_content
        assert "User: Add a feature" in message_content
        assert "Assistant: Done." in message_content
