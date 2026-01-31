import pytest
from dotenv import load_dotenv

from src.agents.web_researcher.tools import google_search_tool, NUM_GOOGLE_RESULTS

load_dotenv(override=True)


def test_google_search_tool():
    """Test the Google Search tool."""
    query = "LangChain"
    results = google_search_tool.invoke(query)

    print(f"\n=== Google Search Results for '{query}' ===\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   Link: {result['link']}")
        print(f"   Snippet: {result['snippet']}")
        print()

    assert isinstance(results, list)
    assert len(results) > 0 and len(results) <= NUM_GOOGLE_RESULTS
    for result in results:
        assert "title" in result
        assert "link" in result
        assert "snippet" in result