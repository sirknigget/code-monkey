from langchain_core.messages import AIMessage

from code_monkey.graph.state import ChatbotState


def orchestrator_node(state: ChatbotState) -> dict:
    """Route or coordinate between other nodes."""
    return {"messages": [AIMessage(content="[orchestrator_node] ready")]}
