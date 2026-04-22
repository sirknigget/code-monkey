import json
import sys
from pathlib import Path

import pytest

from code_monkey.mcp.loader import MCPLoader
from tests.e2e.conftest import FakeModelConfig, run_session
from code_monkey.ui.protocol import InputEvent


FIXTURE_SERVER_PATH = "tests/e2e/mcp_servers/two_tools_server.py"


@pytest.mark.asyncio
async def test_mcp_stdio_server_tools_execute_end_to_end(
    project_dir: Path,
    db_path: Path,
    tmp_path: Path,
    pytestconfig,
) -> None:
    server_path = tmp_path / "two_tools_server.py"
    fixture_source = pytestconfig.rootpath / FIXTURE_SERVER_PATH
    server_path.write_text(fixture_source.read_text())

    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "fixture": {
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": [str(server_path)],
                    "cwd": str(project_dir),
                }
            }
        )
    )

    output_path = project_dir / "mcp-output.txt"
    config = FakeModelConfig(
        orchestrator_responses=[
            _mcp_write_result_call(str(output_path), "MCP wrote this text."),
            "MCP tool finished.",
        ]
    )

    ui = await run_session(
        project_dir,
        [InputEvent("Use MCP to add 3 and 4")],
        db_path,
        model_config=config,
        mcp_client_factory=MCPLoader(config_path),
    )

    assert output_path.read_text() == "MCP wrote this text."
    assert ui.assistant_messages() == [
        "[map_project_node] mapping skipped (no modified files)",
        "MCP tool finished.",
    ]
    assert ui.system_messages() == ["Shutting down..."]


def _mcp_write_result_call(file_path: str, text: str):
    from langchain_core.messages import AIMessage

    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "mcp_write_result",
                "args": {"file_path": file_path, "text": text},
                "id": "call_mcp_1",
                "type": "tool_call",
            }
        ],
    )
