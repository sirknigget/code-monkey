import logging

import pytest
from dotenv import load_dotenv

from code_monkey.agents.web_researcher.tools import (
    NUM_GOOGLE_RESULTS,
    google_search_tool,
)

logger = get_formatted_logger(__name__)

load_dotenv(override=True)


def test_google_search_tool():
    """Test the Google Search tool."""
    query = "LangChain"
    results = google_search_tool.invoke(query)

    logger.info(f"\n=== Google Search Results for '{query}' ===\n")
    for i, result in enumerate(results, 1):
        logger.info(f"{i}. {result['title']}")
        logger.info(f"   Link: {result['link']}")
        logger.info(f"   Snippet: {result['snippet']}")
        logger.info("")

    assert isinstance(results, list)
    assert len(results) > 0 and len(results) <= NUM_GOOGLE_RESULTS
    for result in results:
        assert "title" in result
        assert "link" in result
        assert "snippet" in result
