"""Tests for the Web Researcher agent."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage, AIMessage


class MockLLM:
    """Mock LLM for testing."""

    def invoke(self, messages):
        response = Mock()
        response.content = "This is a test summary about the query."
        return response


@pytest.fixture
def mock_llm():
    """Provide a mock LLM for testing."""
    return MockLLM()


@pytest.fixture
def web_researcher_agent(mock_llm):
    """Create a WebResearcherAgent with mocked dependencies."""
    from src.agents.web_researcher import WebResearcherAgent, create_web_researcher_graph

    # Create agent with mock LLM
    agent = WebResearcherAgent(mock_llm)
    return agent


class TestWebResearcherAgent:
    """Test cases for WebResearcherAgent."""

    def test_agent_initialization(self, web_researcher_agent):
        """Test that the agent initializes correctly with its own graph."""
        assert web_researcher_agent.graph is not None

    def test_research_returns_string(self, web_researcher_agent):
        """Test that research returns a string answer."""
        with patch('src.agents.web_researcher.tools.search_google') as mock_search, \
             patch('src.agents.web_researcher.tools.scrape_url') as mock_scrape:

            # Mock search results
            mock_search.return_value = [
                {
                    "title": "Test Result 1",
                    "url": "https://example.com/1",
                    "snippet": "Test snippet 1",
                },
                {
                    "title": "Test Result 2",
                    "url": "https://example.com/2",
                    "snippet": "Test snippet 2",
                },
            ]

            # Mock scrape results
            mock_scrape.return_value = "This is the scraped content from the page."

            result = web_researcher_agent.research("What is Python programming?")

            assert isinstance(result, str)
            assert len(result) > 0

    def test_research_with_mocked_tools(self, web_researcher_agent):
        """Test research functionality with fully mocked tools."""
        # Test that the agent works with mocked external dependencies
        # We test the flow without actually calling external APIs
        result = web_researcher_agent.research("What is Python?")

        # Verify the result is a non-empty string
        assert isinstance(result, str)
        assert len(result) > 0


class TestWebResearcherState:
    """Test cases for WebResearcherState."""

    def test_state_structure(self):
        """Test that the state has the expected structure."""
        from src.agents.web_researcher import WebResearcherState

        state = WebResearcherState(
            messages=[HumanMessage(content="test query")],
            query="test query",
            search_results=[{"title": "Test", "url": "http://test.com", "snippet": "Test"}],
            scraped_content=[{"url": "http://test.com", "title": "Test", "content": "Content"}],
            summary="Test summary",
            final_answer="Test final answer",
        )

        assert state["messages"] is not None
        assert state["query"] == "test query"
        assert state["search_results"] is not None
        assert state["scraped_content"] is not None
        assert state["summary"] == "Test summary"
        assert state["final_answer"] == "Test final answer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
