from collections.abc import Callable, Coroutine
from typing import Any

from langchain_core.runnables import RunnableConfig

from code_monkey.agents.chat_summarizer.chat_summarizer import ChatSummarizer
from code_monkey.graph.state import ChatbotState


def make_summarizer_node(
    summarizer: ChatSummarizer,
) -> Callable[[ChatbotState, RunnableConfig], Coroutine[Any, Any, dict]]:
    async def summarizer_node(state: ChatbotState, config: RunnableConfig) -> dict:
        summary, last_msgs, span = await summarizer.summarize(
            state["messages"],
            state.get("chat_summary", ""),
            state.get("chat_summary_span", 0),
        )
        return {"chat_summary": summary, "last_messages": last_msgs, "chat_summary_span": span}

    return summarizer_node
