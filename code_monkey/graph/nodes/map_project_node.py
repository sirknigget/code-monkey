from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
from code_monkey.graph.state import ChatbotState


async def map_project_node(state: ChatbotState, config: RunnableConfig) -> dict:
    """Analyze and map the project structure."""
    if not state.get("needs_mapping"):
        return {"needs_mapping": False}

    project_mapper: ProjectMapper = (config.get("configurable") or {})["project_mapper"]
    project_mapper.map_project()

    return {
        "messages": [AIMessage(content="[map_project_node] project mapped")],
        "needs_mapping": False,
    }
