from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
from code_monkey.graph.state import ChatbotState


async def map_project_node(state: ChatbotState, config: RunnableConfig) -> dict:
    """Analyze and map the project structure."""
    if not state.get("needs_mapping"):
        return {"needs_mapping": False}

    project_mapper: ProjectMapper = (config.get("configurable") or {})["project_mapper"]
    mapping_done = await project_mapper.map_project()

    message = (
        "[map_project_node] project mapped"
        if mapping_done
        else "[map_project_node] mapping skipped (no modified files)"
    )

    return {
        "messages": [AIMessage(content=message)],
        "needs_mapping": False,
    }
