from collections.abc import Callable, Coroutine
from typing import Any

from langchain_core.runnables import RunnableConfig

from code_monkey.agents.chat_summarizer.chat_summarizer import ChatSummarizer
from code_monkey.graph.state import ChatbotState


def make_summarizer_node(
    summarizer: ChatSummarizer,
) -> Callable[[ChatbotState, RunnableConfig], Coroutine[Any, Any, dict]]:
    async def summarizer_node(state: ChatbotState, config: RunnableConfig) -> dict:
        result = await summarizer.summarize(
            state["messages"],
            state.get("chat_summary", ""),
            state.get("chat_summary_span", 0),
        )
        return {"chat_summary": result.summary, "last_messages": result.last_messages, "chat_summary_span": result.span}

    return summarizer_node
