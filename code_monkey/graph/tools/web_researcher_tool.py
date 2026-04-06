from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from code_monkey.agents.web_researcher.web_researcher import WebResearcher


class WebSearchInput(BaseModel):
    query: str = Field(description="The search query to research on the web")
    thread_id: str = Field(
        default="", description="Optional thread ID to reuse a prior research session"
    )


async def _web_search(
    query: str, thread_id: str = "", *, config: RunnableConfig
) -> str:
    researcher: WebResearcher = (config.get("configurable") or {})["web_researcher"]
    result = await researcher.search(query, thread_id or None)
    return result.result


web_researcher_tool = StructuredTool.from_function(
    coroutine=_web_search,
    name="web_search",
    description="Search the web for up-to-date information on a given query.",
    args_schema=WebSearchInput,
)
