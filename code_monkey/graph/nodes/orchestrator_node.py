from collections.abc import Callable, Coroutine
from typing import Any

from langchain_core.language_models import BaseChatModel

from code_monkey.graph.state import ChatbotState


def make_orchestrator_node(
    model: BaseChatModel,
) -> Callable[[ChatbotState], Coroutine[Any, Any, dict]]:
    """Return an async LangGraph node function that invokes *model* on each turn."""

    async def orchestrator_node(state: ChatbotState) -> dict:
        response = await model.ainvoke(state["messages"])
        return {"messages": [response]}

    return orchestrator_node
