from unittest.mock import AsyncMock, MagicMock

import pytest

from code_monkey.agents.web_researcher.web_researcher import SearchResult, WebResearcher
from code_monkey.graph.tools.web_researcher_tool import web_researcher_tool


@pytest.fixture
def mock_researcher():
    researcher = MagicMock(spec=WebResearcher)
    researcher.search = AsyncMock(
        return_value=SearchResult(result="BTC is at $60,000", thread_id="abc123")
    )
    return researcher


@pytest.mark.asyncio
async def test_web_researcher_tool_returns_result(mock_researcher):
    result = await web_researcher_tool.ainvoke(
        {"query": "What is the price of BTC?", "thread_id": "abc123"},
        config={"configurable": {"web_researcher": mock_researcher}},
    )

    assert result == "BTC is at $60,000"
    mock_researcher.search.assert_called_once_with(
        "What is the price of BTC?", "abc123"
    )


@pytest.mark.asyncio
async def test_web_researcher_tool_uses_none_when_thread_id_empty(mock_researcher):
    await web_researcher_tool.ainvoke(
        {"query": "latest news", "thread_id": ""},
        config={"configurable": {"web_researcher": mock_researcher}},
    )

    mock_researcher.search.assert_called_once_with("latest news", None)
