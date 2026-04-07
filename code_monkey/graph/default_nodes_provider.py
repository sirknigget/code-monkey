from langgraph.prebuilt import ToolNode

from code_monkey.agents.web_researcher.web_researcher import WebResearcher
from code_monkey.graph.nodes.map_project_node import map_project_node
from code_monkey.graph.nodes.orchestrator_node import make_orchestrator_node
from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState
from code_monkey.graph.tools.bash_tool import bash_tool
from code_monkey.graph.tools.file_tools import create_file_tools
from code_monkey.graph.tools.web_researcher_tool import web_researcher_tool
from code_monkey.models.model_config import ModelConfig


class DefaultNodesProvider(NodesProvider):
    def __init__(
        self, tool_node: ToolNode, orchestrator_node_fn, researcher: WebResearcher
    ) -> None:
        self._tool_node = tool_node
        self._orchestrator_node = orchestrator_node_fn
        self._researcher = researcher

    @classmethod
    async def create(
        cls, project_root: str, model_config: ModelConfig
    ) -> "DefaultNodesProvider":
        researcher = await WebResearcher.create(
            model=model_config.web_researcher_model()
        )
        tools = [
            web_researcher_tool,
            *create_file_tools(root_dir=project_root),
            bash_tool,
        ]
        tool_node = ToolNode(tools)
        orchestrator_node_fn = make_orchestrator_node(
            model_config.orchestrator_model().bind_tools(tools)
        )
        return cls(tool_node, orchestrator_node_fn, researcher)

    def configurable_fields(self) -> dict:
        return {"web_researcher": self._researcher}

    async def map_project_node(self, state: ChatbotState) -> dict:
        return map_project_node(state)

    async def orchestrator_node(self, state: ChatbotState) -> dict:
        return await self._orchestrator_node(state)

    async def tool_node(self, state: ChatbotState) -> dict:
        return await self._tool_node.ainvoke(state)

    async def teardown(self) -> None:
        await self._researcher.teardown()
