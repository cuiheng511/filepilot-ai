import asyncio
import importlib.util
import os
import sys
from pathlib import Path

import pytest

from filepilot.mcp.server import build_tools, create_server, parse_args


@pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="MCP SDK not installed")
def test_create_server_registers_expected_tools(tmp_path: Path):
    allowed = tmp_path / "workspace"
    allowed.mkdir()
    args = parse_args(["--allow", str(allowed), "--plan-dir", str(tmp_path / "plans")])

    server = create_server(build_tools(args))

    tools = set(server._tool_manager._tools)
    assert {
        "server_status",
        "list_workflow_templates",
        "get_workflow_template",
        "mcp_client_config",
        "scan_files",
        "search_files",
        "index_folder",
        "search_index",
        "read_file",
        "extract_file_text",
        "summarize_file",
        "suggest_tags",
        "add_tags",
        "find_duplicates",
        "propose_organization_plan",
        "list_plans",
        "cleanup_plans",
        "apply_organization_plan",
        "undo_organization_plan",
    }.issubset(tools)


@pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="MCP SDK not installed")
def test_stdio_protocol_lists_registered_tools(tmp_path: Path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def list_tool_names() -> dict[str, str | None]:
        allowed = tmp_path / "workspace"
        allowed.mkdir()
        params = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "filepilot.mcp.server",
                "--allow",
                str(allowed),
                "--plan-dir",
                str(tmp_path / "plans"),
                "--read-only",
            ],
            cwd=Path.cwd(),
            env=os.environ.copy(),
        )
        with open(os.devnull, "w") as errlog:
            async with (
                stdio_client(params, errlog=errlog) as (
                    read,
                    write,
                ),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                result = await session.list_tools()
                return {tool.name: tool.description for tool in result.tools}

    tools = asyncio.run(list_tool_names())

    assert len(tools) >= 19
    assert tools["server_status"] == "Show allowed directories, write mode, and safety limits."
    assert tools["scan_files"] == "Scan local files under an allowed directory."
    assert tools["propose_organization_plan"] == (
        "Create a dry-run file organization plan. This never moves files."
    )


def test_read_only_flag_overrides_write_enabled_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    allowed = tmp_path / "workspace"
    allowed.mkdir()
    monkeypatch.setenv("FILEPILOT_MCP_WRITE_ENABLED", "true")
    args = parse_args(["--allow", str(allowed), "--read-only"])

    tools = build_tools(args)

    assert tools.server_status()["write_enabled"] is False
