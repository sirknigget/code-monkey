import uuid
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import Field, BaseModel

from code_monkey.agents.web_researcher.tools import PlaywrightTools, google_search_tool
from code_monkey.utils.langchain_utils import last_message_content


class SearchResult(BaseModel):
    result: str = Field(description="The result of the web search")
    thread_id: str = Field(description="The thread ID for this search session")


system_prompt: str = (
    "You are a web researcher agent. You can use tools to navigate the web, "
    "perform searches, and gather information to answer user queries."
)


class WebResearcher:
    """An agent that can perform web research using various tools."""

    _playwright_tools: PlaywrightTools

    def __init__(self, playwright_tools, agent: Any):
        self._playwright_tools = playwright_tools
        self._agent = agent

    @classmethod
    async def create(cls, model, headless: bool = True):
        playwright_tools = await PlaywrightTools.initialize(headless=headless)
        tools = playwright_tools.get_tools() + [google_search_tool]
        agent = create_agent(
            model=model,
            tools=tools,
            checkpointer=InMemorySaver(),
            system_prompt=system_prompt)

        return cls(playwright_tools, agent)

    async def search(self, query, thread_id: str = None) -> SearchResult:
        """Perform a web search using the agent."""
        if thread_id is None:
            thread_id = uuid.uuid4().hex
        messages = [HumanMessage(content=query)]
        response = await self._agent.ainvoke({"messages": messages},
                                             config=RunnableConfig(configurable={"thread_id": thread_id}))
        result = last_message_content(response)
        return SearchResult(result=result, thread_id=thread_id)

    async def teardown(self):
        """Teardown the Playwright tools."""
        await self._playwright_tools.teardown()
