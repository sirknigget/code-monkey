from typing import List, Dict

from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools import tool
from playwright.async_api import async_playwright

NUM_GOOGLE_RESULTS = 10


@tool
def google_search_tool(query: str) -> List[Dict[str, str]]:
    """Search Google for the given query using Serper API."""

    google_serper = GoogleSerperAPIWrapper()
    result = google_serper.results(query)
    return result["organic"][:NUM_GOOGLE_RESULTS]


class PlaywrightTools:
    """Manages Playwright browser tools lifecycle."""

    def __init__(self, playwright, browser, tools):
        self._playwright = playwright
        self._browser = browser
        self._tools = tools

    @classmethod
    async def initialize(cls, headless: bool = False):
        """Initialize Playwright, browser, and tools."""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=headless)
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser)
        tools = toolkit.get_tools()
        return cls(playwright, browser, tools)

    def get_tools(self):
        """Get the list of Playwright tools."""
        return self._tools

    async def teardown(self):
        """Gracefully close browser and playwright."""
        await self._browser.close()
        await self._playwright.stop()
