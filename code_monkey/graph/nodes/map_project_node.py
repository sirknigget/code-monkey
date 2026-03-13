from langchain_core.messages import AIMessage

from code_monkey.graph.state import ChatbotState


def map_project_node(state: ChatbotState) -> dict:
    """Analyze and map the project structure."""
    return {
        "messages": [AIMessage(content="[map_project_node] project mapped")],
        "needs_mapping": False,
    }
