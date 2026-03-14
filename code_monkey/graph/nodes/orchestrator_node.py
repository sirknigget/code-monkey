from collections.abc import Callable

from langchain_core.language_models import BaseChatModel

from code_monkey.graph.state import ChatbotState


def make_orchestrator_node(model: BaseChatModel) -> Callable[[ChatbotState], dict]:
    """Return a LangGraph node function that invokes *model* on each turn."""

    def orchestrator_node(state: ChatbotState) -> dict:
        response = model.invoke(state["messages"])
        return {"messages": [response]}

    return orchestrator_node
