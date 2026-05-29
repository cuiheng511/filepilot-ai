import importlib.util
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
        "apply_organization_plan",
        "undo_organization_plan",
    }.issubset(tools)
