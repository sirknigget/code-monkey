import json
from pathlib import Path
from typing import cast

import pytest
from langchain_mcp_adapters.sessions import Connection

from code_monkey.mcp.config import DEFAULT_MCP_CONFIG_PATH, load_mcp_config, save_mcp_config


def test_save_and_load_round_trip_for_stdio_and_http_servers(tmp_path: Path) -> None:
    config_path = tmp_path / "mcp.json"
    servers: dict[str, Connection] = {
        "math": {
            "transport": "stdio",
            "command": "python",
            "args": ["server.py"],
            "env": {"DEBUG": "1"},
            "cwd": "/tmp/project",
        },
        "weather": cast(
            Connection,
            {
                "transport": "http",
                "url": "http://localhost:8000/mcp",
                "headers": {"Authorization": "Bearer token"},
                "timeout": 10,
            },
        ),
    }

    save_mcp_config(servers, config_path)

    assert load_mcp_config(config_path) == servers


def test_load_missing_file_returns_empty_config(tmp_path: Path) -> None:
    assert load_mcp_config(tmp_path / "missing.json") == {}


def test_explicit_path_override_does_not_use_default_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    default_path = tmp_path / "default.json"
    override_path = tmp_path / "override.json"
    monkeypatch.setattr("code_monkey.mcp.config.DEFAULT_MCP_CONFIG_PATH", default_path)

    default_path.write_text(json.dumps({"default": {"transport": "stdio", "command": "python", "args": ["default.py"]}}))
    override_config = {
        "override": {
            "transport": "stdio",
            "command": "python",
            "args": ["override.py"],
        }
    }
    override_path.write_text(json.dumps(override_config))

    assert load_mcp_config(override_path) == override_config


def test_default_path_constant_is_expanded() -> None:
    assert DEFAULT_MCP_CONFIG_PATH.is_absolute()
