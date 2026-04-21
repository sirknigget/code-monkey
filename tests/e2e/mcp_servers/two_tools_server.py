from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TwoToolsServer")


@mcp.tool()
def mcp_add(a: int, b: int) -> int:
    return a + b


@mcp.tool()
def mcp_repeat(text: str, count: int) -> str:
    return text * count


if __name__ == "__main__":
    mcp.run(transport="stdio")
