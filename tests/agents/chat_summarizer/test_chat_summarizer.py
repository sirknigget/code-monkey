"""Tests for the ChatSummarizer class."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from code_monkey.agents.chat_summarizer.chat_summarizer import ChatSummarizer


class MockLLM:
    """Fake BaseChatModel that returns a fixed AIMessage and tracks call count."""

    def __init__(self, response: str = "Updated summary.") -> None:
        self._response = response
        self.call_count = 0

    async def ainvoke(self, messages, **kwargs):
        self.call_count += 1
        return AIMessage(content=self._response)


@pytest.fixture
def mock_llm():
    return MockLLM()


@pytest.fixture
def summarizer(mock_llm):
    return ChatSummarizer(mock_llm)


@pytest.mark.asyncio
async def test_first_turn_no_prior_messages(summarizer, mock_llm):
    """First turn: single HumanMessage, nothing to summarize — LLM not called."""
    messages = [HumanMessage(content="Hello")]

    summary, last_messages, span = await summarizer.summarize(
        messages, existing_summary="", chat_summary_span=0
    )

    assert summary == ""
    assert last_messages == [HumanMessage(content="Hello")]
    assert span == 0
    assert mock_llm.call_count == 0


@pytest.mark.asyncio
async def test_multi_turn_compresses_prior_history(mock_llm):
    """Multi-turn: prior human+AI messages are passed to LLM for compression."""
    messages = [
        HumanMessage(content="First question"),
        AIMessage(content="First answer"),
        HumanMessage(content="Second question"),
        AIMessage(content="Second answer"),
        HumanMessage(content="Third question"),
    ]
    summarizer = ChatSummarizer(mock_llm)

    summary, last_messages, span = await summarizer.summarize(
        messages, existing_summary="Prior summary.", chat_summary_span=0
    )

    # LLM should have been called once to compress prior history
    assert mock_llm.call_count == 1
    assert summary == "Updated summary."
    # last_messages starts from the last HumanMessage
    assert last_messages == [HumanMessage(content="Third question")]
    # span advances to the index of the last HumanMessage in filtered list (index 4)
    assert span == 4


@pytest.mark.asyncio
async def test_nothing_new_to_summarize(mock_llm):
    """Span already points past all prior messages — LLM not called."""
    messages = [
        HumanMessage(content="First question"),
        AIMessage(content="First answer"),
        HumanMessage(content="Second question"),
    ]
    summarizer = ChatSummarizer(mock_llm)

    # chat_summary_span=2 means everything up to index 2 in filtered is already summarized.
    # filtered = [HumanMessage("First question"), AIMessage("First answer"), HumanMessage("Second question")]
    # last_user_idx = 2, to_summarize = filtered[2:2] = [] → empty
    summary, last_messages, span = await summarizer.summarize(
        messages, existing_summary="Already summarized.", chat_summary_span=2
    )

    assert mock_llm.call_count == 0
    assert summary == "Already summarized."
    assert last_messages == [HumanMessage(content="Second question")]
    assert span == 2


@pytest.mark.asyncio
async def test_tool_call_messages_filtered_out(mock_llm):
    """AIMessages with tool_calls are excluded from filtered messages."""
    tool_ai_msg = AIMessage(
        content="",
        tool_calls=[{"name": "bash", "args": {"command": "ls"}, "id": "call_1"}],
    )
    messages = [
        HumanMessage(content="Run ls"),
        tool_ai_msg,
        AIMessage(content="Here are the files."),
        HumanMessage(content="Thanks"),
    ]
    summarizer = ChatSummarizer(mock_llm)

    summary, last_messages, span = await summarizer.summarize(
        messages, existing_summary="", chat_summary_span=0
    )

    # filtered = [HumanMessage("Run ls"), AIMessage("Here are the files."), HumanMessage("Thanks")]
    # last_user_idx = 2; to_summarize = filtered[0:2] → non-empty → LLM called
    assert mock_llm.call_count == 1
    # tool_ai_msg must NOT appear in last_messages
    assert tool_ai_msg not in last_messages
    assert last_messages == [HumanMessage(content="Thanks")]
    assert span == 2
