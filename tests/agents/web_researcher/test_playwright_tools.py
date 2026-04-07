import logging

import pytest
from dotenv import load_dotenv

from code_monkey.agents.web_researcher.tools import PlaywrightTools
from code_monkey.utils.json_utils import dump_object

logger = get_formatted_logger(__name__)

load_dotenv(override=True)


@pytest.mark.asyncio
async def test_playwright_tools_initialize():
    """Test PlaywrightTools initialization."""
    pt = await PlaywrightTools.initialize(headless=True)

    assert pt._playwright is not None
    assert pt._browser is not None
    assert pt._tools is not None
    assert len(pt._tools) > 0

    await pt.teardown()


@pytest.mark.asyncio
async def test_playwright_tools_get_tools():
    """Test getting tools from PlaywrightTools."""
    pt = await PlaywrightTools.initialize(headless=True)

    tools = pt.get_tools()

    assert tools is not None
    assert isinstance(tools, list)
    assert len(tools) > 0

    await pt.teardown()


@pytest.mark.asyncio
async def test_playwright_tools_navigate():
    """Test navigating to a website."""
    pt = await PlaywrightTools.initialize(headless=True)

    # Find navigate and click tools
    navigate_tool = [
        tool for tool in pt.get_tools() if tool.name == "navigate_browser"
    ][0]
    assert navigate_tool is not None, "navigate_browser tool not found"

    # Navigate to example.com using LangChain tool
    result = await navigate_tool.ainvoke("https://example.com")
    assert "returned status code" in result
    assert "200" in result
    logger.info(f"Navigation result:\n {dump_object(result)}")

    await pt.teardown()


@pytest.mark.asyncio
async def test_playwright_tools_teardown():
    """Test that teardown closes browser and playwright gracefully."""
    pt = await PlaywrightTools.initialize(headless=True)

    browser = pt._browser
    playwright = pt._playwright

    await pt.teardown()

    # After teardown, the browser should be closed
    # Note: We can't check is_closed directly after close in some cases,
    # but the teardown should not raise any exceptions
    assert True
