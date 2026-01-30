from typing import List, Dict

from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools import tool
from playwright.async_api import async_playwright

NUM_GOOGLE_RESULTS = 10

@tool
def google_search(query: str) -> List[Dict[str, str]]:
    """Search Google for the given query using Serper API."""

    google_serper = GoogleSerperAPIWrapper()
    result = google_serper.results(query)
    return result["organic"][:NUM_GOOGLE_RESULTS]

async def playwright_tools():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser)
    return toolkit.get_tools(), browser, playwright