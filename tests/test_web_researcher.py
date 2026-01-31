import pytest
import asyncio
from dotenv import load_dotenv

from src.agents.web_researcher.web_researcher import WebResearcher

load_dotenv(override=True)


@pytest.mark.asyncio
async def test_web_researcher_search():
    """Test the WebResearcher agent with a query about LangChain."""
    from langchain_anthropic import ChatAnthropic

    model = ChatAnthropic(model="MiniMax-M2.1", anthropic_api_url="https://api.minimax.io/anthropic")
    researcher = await WebResearcher.create(model=model, headless=True)

    query = "What is the latest price of BTC and its recent trend?"
    result = await researcher.search(query)

    print(f"\n=== Web Researcher Result for '{query}' ===")
    print(f"Thread ID: {result.thread_id}")
    print(f"Result: {result.result}")
    print()

    assert result is not None
    assert result.thread_id is not None
    assert isinstance(result.thread_id, str)
    assert len(result.thread_id) > 0
    assert result.result is not None
    assert isinstance(result.result, str)
    assert len(result.result) > 0

    await researcher.teardown()
