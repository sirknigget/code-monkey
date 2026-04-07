from abc import ABC, abstractmethod

from langchain_core.runnables import RunnableConfig

from code_monkey.graph.state import ChatbotState


class NodesProvider(ABC):
    @abstractmethod
    async def map_project_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        """Analyze and map the project structure."""

    @abstractmethod
    async def orchestrator_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        """Route or coordinate between other nodes."""

    @abstractmethod
    async def tool_node(self, state: ChatbotState) -> dict:
        """Execute tool calls from the last AI message."""

    def configurable_fields(self) -> dict:
        """Return extra fields to merge into RunnableConfig.configurable. No-op by default."""
        return {}

    async def teardown(self) -> None:
        """Release any resources held by this provider. No-op by default."""
