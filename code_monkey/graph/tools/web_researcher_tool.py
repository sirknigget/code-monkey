import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from code_monkey.agents.web_researcher.web_researcher import WebResearcher

_executor = ThreadPoolExecutor(max_workers=4)


class WebSearchInput(BaseModel):
    query: str = Field(description="The search query to research on the web")
    thread_id: str = Field(
        default="", description="Optional thread ID to reuse a prior research session"
    )


def create_web_researcher_tool(researcher: WebResearcher) -> StructuredTool:
    """Create a LangChain tool wrapping the given WebResearcher instance."""

    async def web_search(query: str, thread_id: str = "") -> str:
        result = await researcher.search(query, thread_id or None)
        return result.result

    def sync_web_search(query: str, thread_id: str = "") -> str:
        return _executor.submit(asyncio.run, web_search(query, thread_id)).result()

    return StructuredTool.from_function(
        func=sync_web_search,
        coroutine=web_search,
        name="web_search",
        description="Search the web for up-to-date information on a given query.",
        args_schema=WebSearchInput,
    )
