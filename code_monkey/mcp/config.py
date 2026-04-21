import json
from pathlib import Path
from typing import Any, cast

from langchain_mcp_adapters.sessions import Connection

DEFAULT_MCP_CONFIG_PATH = Path("~/.codemonkey/mcp.json").expanduser()


def load_mcp_config(config_path: Path = DEFAULT_MCP_CONFIG_PATH) -> dict[str, Connection]:
    if not config_path.exists():
        return {}
    with config_path.open() as f:
        raw = json.load(f)
    return _parse_mcp_config(raw)


def save_mcp_config(
    servers: dict[str, Connection], config_path: Path = DEFAULT_MCP_CONFIG_PATH
) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w") as f:
        json.dump(servers, f, indent=2)
        f.write("\n")


def _parse_mcp_config(raw: Any) -> dict[str, Connection]:
    if not isinstance(raw, dict):
        raise ValueError("MCP config must be a JSON object mapping server names to configs.")
    return {server_name: _parse_connection(server_name, value) for server_name, value in raw.items()}


def _parse_connection(server_name: str, value: Any) -> Connection:
    if not isinstance(server_name, str) or not server_name:
        raise ValueError("MCP config server names must be non-empty strings.")
    if not isinstance(value, dict):
        raise ValueError(f"MCP config for server '{server_name}' must be a JSON object.")
    transport = value.get("transport")
    if transport not in {"stdio", "sse", "http", "streamable_http", "streamable-http", "websocket"}:
        raise ValueError(
            f"MCP config for server '{server_name}' has unsupported transport '{transport}'."
        )
    return cast(Connection, value)
