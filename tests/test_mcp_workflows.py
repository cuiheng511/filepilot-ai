from pathlib import Path

import pytest

from filepilot.mcp.security import MCPSecurityConfig, PathGuard
from filepilot.mcp.tools import FilePilotMCPTools
from filepilot.mcp.workflows import get_template, list_templates


def test_list_templates_can_hide_write_workflows():
    templates = list_templates(include_write=False)

    assert templates
    assert all(template["requires_write"] is False for template in templates)
    assert {template["id"] for template in templates} >= {
        "safe_inventory",
        "document_brief",
        "organization_plan",
    }


def test_get_template_returns_full_prompt():
    template = get_template("duplicate-review")

    assert template["id"] == "duplicate_review"
    assert "prompt" in template
    assert "Do not delete files" in template["prompt"]
    assert "find_duplicates" in template["tools"]


def test_get_template_rejects_unknown_id():
    with pytest.raises(ValueError, match="Unknown workflow template"):
        get_template("unknown")


def test_tools_generate_client_config_from_allowed_roots(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root,)))
    tools = FilePilotMCPTools(guard)

    result = tools.mcp_client_config("cursor")

    server = result["config"]["mcpServers"]["filepilot"]
    assert result["client"] == "cursor"
    assert server["command"] == "filepilot-mcp"
    assert server["args"] == ["--allow", str(root.resolve()), "--read-only"]


def test_tools_generate_write_config_only_when_requested(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root,)))
    tools = FilePilotMCPTools(guard)

    result = tools.mcp_client_config("claude-code", include_write=True)

    assert result["client"] == "claude_code"
    assert result["config"]["mcpServers"]["filepilot"]["args"][-1] == "--write"


def test_tools_list_workflow_templates_includes_modes(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    tools = FilePilotMCPTools(PathGuard(MCPSecurityConfig(allowed_dirs=(root,))))

    result = tools.list_workflow_templates()

    assert result["count"] >= 6
    assert {"id", "title", "mode", "requires_write", "tools", "description"} <= set(
        result["templates"][0]
    )
