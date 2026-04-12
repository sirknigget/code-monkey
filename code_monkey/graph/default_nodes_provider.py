from pathlib import Path

from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode
from langgraph.types import StreamWriter

from code_monkey.agents.chat_summarizer.chat_summarizer import ChatSummarizer
from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.agents.tester.tester import Tester
from code_monkey.agents.web_researcher.web_researcher import WebResearcher
from code_monkey.graph.nodes.map_project_node import map_project_node
from code_monkey.graph.nodes.orchestrator_node import make_orchestrator_node
from code_monkey.graph.nodes.review_router_node import make_review_router_node
from code_monkey.graph.nodes.summarizer_node import make_summarizer_node
from code_monkey.graph.nodes.tester_node import make_tester_node
from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState
from code_monkey.graph.tools.bash_tool import create_bash_tool
from code_monkey.graph.tools.file_tools import create_file_tools
from code_monkey.graph.tools.web_researcher_tool import web_researcher_tool
from code_monkey.models.model_config import ModelConfig


class DefaultNodesProvider(NodesProvider):
    def __init__(
        self,
        tool_node: ToolNode,
        orchestrator_node_fn,
        researcher: WebResearcher,
        project_mapper: ProjectMapper,
        summarizer_node_fn,
        tester_node_fn,
        review_router_node_fn,
    ) -> None:
        self._tool_node = tool_node
        self._orchestrator_node = orchestrator_node_fn
        self._researcher = researcher
        self._project_mapper = project_mapper
        self._summarizer_node = summarizer_node_fn
        self._tester_node = tester_node_fn
        self._review_router_node = review_router_node_fn

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
            create_bash_tool(root_dir=project_root),
        ]
        tool_node = ToolNode(tools)
        orchestrator_node_fn = make_orchestrator_node(
            model_config.orchestrator_model(), tools
        )
        summarizer = Summarizer(
            llm=model_config.summarizer_model(), working_dir=Path(project_root)
        )
        project_mapper = ProjectMapper(
            working_dir=Path(project_root), summarizer=summarizer
        )
        tester_bash_tool = create_bash_tool(root_dir=project_root)
        chat_summarizer = ChatSummarizer(model_config.chat_summarizer_model())
        tester = Tester(model_config.tester_model(), tester_bash_tool)
        summarizer_node_fn = make_summarizer_node(chat_summarizer)
        tester_node_fn = make_tester_node(tester)
        review_router_node_fn = make_review_router_node()
        return cls(
            tool_node,
            orchestrator_node_fn,
            researcher,
            project_mapper,
            summarizer_node_fn,
            tester_node_fn,
            review_router_node_fn,
        )

    def configurable_fields(self) -> dict:
        return {
            "web_researcher": self._researcher,
            "project_mapper": self._project_mapper,
        }

    async def map_project_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        return await map_project_node(state, config)

    async def orchestrator_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        return await self._orchestrator_node(state, config)

    async def tool_node(self, state: ChatbotState) -> dict:
        return await self._tool_node.ainvoke(state)

    async def summarizer_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        return await self._summarizer_node(state, config)

    async def tester_node(
        self, state: ChatbotState, config: RunnableConfig, *, writer: StreamWriter
    ) -> dict:
        return await self._tester_node(state, config, writer=writer)

    async def review_router_node(
        self, state: ChatbotState, config: RunnableConfig, *, writer: StreamWriter
    ) -> dict:
        return await self._review_router_node(state, config, writer=writer)

    async def teardown(self) -> None:
        await self._researcher.teardown()
