from pathlib import Path

import pytest

from filepilot.mcp.security import MCPAccessError, MCPSecurityConfig, PathGuard
from filepilot.mcp.tools import FilePilotMCPTools


@pytest.fixture
def mcp_tools(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "alpha.txt").write_text("alpha notes about invoices", encoding="utf-8")
    (root / "beta.md").write_text("# Beta\n\nProject notes", encoding="utf-8")
    (root / "copy-a.txt").write_text("duplicate", encoding="utf-8")
    (root / "copy-b.txt").write_text("duplicate", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir()
    (nested / "script.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root,), max_read_chars=20))
    return FilePilotMCPTools(guard, index_dir=tmp_path / "index"), root


def test_scan_files_returns_metadata(mcp_tools):
    tools, root = mcp_tools

    result = tools.scan_files(str(root), recursive=False)

    assert result["root"] == str(root.resolve())
    assert result["count"] == 4
    assert {item["name"] for item in result["files"]} >= {"alpha.txt", "beta.md"}


def test_search_files_matches_name(mcp_tools):
    tools, root = mcp_tools

    result = tools.search_files(str(root), "alpha")

    assert result["count"] == 1
    assert result["results"][0]["name"] == "alpha.txt"


def test_read_file_is_bounded_by_security_config(mcp_tools):
    tools, root = mcp_tools

    result = tools.read_file(str(root / "alpha.txt"), max_chars=200)

    assert result["returned_chars"] == 20
    assert result["truncated"] is True


def test_extract_file_text_reads_markdown(mcp_tools):
    tools, root = mcp_tools

    result = tools.extract_file_text(str(root / "beta.md"))

    assert "Beta" in result["content"]


def test_find_duplicates_groups_exact_matches(mcp_tools):
    tools, root = mcp_tools

    result = tools.find_duplicates(str(root))

    duplicate_files = result["duplicates"][0]["files"]
    assert any(path.endswith("copy-a.txt") for path in duplicate_files)
    assert any(path.endswith("copy-b.txt") for path in duplicate_files)


def test_propose_organization_plan_is_dry_run(mcp_tools, tmp_path: Path):
    tools, root = mcp_tools
    target = tmp_path / "organized"

    result = tools.propose_organization_plan(str(root), str(target), rules=["extension"])

    assert result["dry_run"] is True
    assert result["count"] >= 4
    assert (root / "alpha.txt").exists()
    assert not target.exists()


def test_add_tags_requires_write_mode(mcp_tools):
    tools, root = mcp_tools

    with pytest.raises(MCPAccessError):
        tools.add_tags(str(root / "alpha.txt"), ["invoice"])
