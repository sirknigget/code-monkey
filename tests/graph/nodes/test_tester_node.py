"""Unit tests for the tester_node wrapper."""

from __future__ import annotations

import pytest
from langchain_core.runnables import RunnableConfig
from unittest.mock import AsyncMock, MagicMock

from code_monkey.agents.tester.tester import Tester, TesterResult
from code_monkey.graph.nodes.tester_node import make_tester_node
from code_monkey.graph.state import ChatbotState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    chat_summary: str = "",
    last_messages: list | None = None,
) -> ChatbotState:
    return ChatbotState(
        messages=[],
        needs_mapping=False,
        review_feedback=None,
        iteration_count=0,
        chat_summary=chat_summary,
        last_messages=last_messages or [],
        chat_summary_span=0,
        tester_result=None,
    )


def _make_config(project_mapper=None) -> RunnableConfig:
    configurable = {}
    if project_mapper is not None:
        configurable["project_mapper"] = project_mapper
    return RunnableConfig(configurable=configurable)


def _make_mock_tester(result: TesterResult) -> MagicMock:
    mock = MagicMock(spec=Tester)
    mock.run = AsyncMock(return_value=result)
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTesterNode:
    @pytest.mark.asyncio
    async def test_pass_sets_review_feedback_to_none_writer_not_called(self) -> None:
        """When tester passes, review_feedback is None and writer is never called."""
        tester = _make_mock_tester(TesterResult(status="passed", reason=""))
        node = make_tester_node(tester)
        writer = MagicMock()
        state = _make_state()

        result = await node(state, _make_config(), writer=writer)

        assert result == {
            "tester_result": TesterResult(status="passed", reason=""),
            "review_feedback": None,
        }
        writer.assert_not_called()

    @pytest.mark.asyncio
    async def test_fail_sets_review_feedback_writer_not_called(self) -> None:
        """When tester fails, tester_node returns feedback but no routing policy."""
        reason = "2 tests failed"
        tester = _make_mock_tester(TesterResult(status="failed", reason=reason))
        node = make_tester_node(tester)
        writer = MagicMock()
        state = _make_state()

        result = await node(state, _make_config(), writer=writer)

        assert result == {
            "tester_result": TesterResult(status="failed", reason=reason),
            "review_feedback": reason,
        }
        writer.assert_not_called()
