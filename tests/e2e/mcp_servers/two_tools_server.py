from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TwoToolsServer")


@mcp.tool()
def mcp_add(a: int, b: int) -> int:
    return a + b


@mcp.tool()
def mcp_repeat(text: str, count: int) -> str:
    return text * count


@mcp.tool()
def mcp_write_result(file_path: str, text: str) -> str:
    Path(file_path).write_text(text)
    return text


if __name__ == "__main__":
    mcp.run(transport="stdio")
