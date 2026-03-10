import logging

import pytest
from dotenv import load_dotenv

from code_monkey.agents.web_researcher.web_researcher import WebResearcher
from code_monkey.models.models import get_minimax_model, get_openai_model

logger = logging.getLogger(__name__)

load_dotenv(override=True)


@pytest.mark.asyncio
async def test_web_researcher_search():
    """Test the WebResearcher agent with a query about LangChain."""
    model = get_openai_model()
    researcher = await WebResearcher.create(model=model, headless=True)

    query = "What is the latest price of BTC and its recent trend?"
    result = await researcher.search(query)

    logger.info(f"\n=== Web Researcher Result for '{query}' ===")
    logger.info(f"Thread ID: {result.thread_id}")
    logger.info(f"Result: {result.result}")
    logger.info("")

    assert result is not None
    assert result.thread_id is not None
    assert isinstance(result.thread_id, str)
    assert len(result.thread_id) > 0
    assert result.result is not None
    assert isinstance(result.result, str)
    assert len(result.result) > 0

    await researcher.teardown()
