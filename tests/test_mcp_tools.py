import json
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
    return FilePilotMCPTools(guard, index_dir=tmp_path / "index", plan_dir=tmp_path / "plans"), root


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

    assert result["plan_id"]
    assert result["dry_run"] is True
    assert result["count"] >= 4
    assert (root / "alpha.txt").exists()
    assert not target.exists()


def test_add_tags_requires_write_mode(mcp_tools):
    tools, root = mcp_tools

    with pytest.raises(MCPAccessError):
        tools.add_tags(str(root / "alpha.txt"), ["invoice"])


def test_search_index_filters_results_outside_current_allowlist(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "allowed.txt").write_text("shared needle in allowed folder", encoding="utf-8")
    (second / "stale.txt").write_text("shared needle in stale folder", encoding="utf-8")
    index_dir = tmp_path / "index"

    broad_guard = PathGuard(MCPSecurityConfig(allowed_dirs=(first, second)))
    broad_tools = FilePilotMCPTools(broad_guard, index_dir=index_dir)
    broad_tools.index_folder(str(first))
    broad_tools.index_folder(str(second))

    narrow_guard = PathGuard(MCPSecurityConfig(allowed_dirs=(first,)))
    narrow_tools = FilePilotMCPTools(narrow_guard, index_dir=index_dir)
    result = narrow_tools.search_index("needle", limit=10)

    result_paths = {Path(item["path"]).name for item in result["results"]}
    assert result_paths == {"allowed.txt"}


def test_search_index_root_scope_filters_allowed_sibling(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "alpha.txt").write_text("project needle alpha", encoding="utf-8")
    (second / "beta.txt").write_text("project needle beta", encoding="utf-8")
    index_dir = tmp_path / "index"

    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(first, second)))
    tools = FilePilotMCPTools(guard, index_dir=index_dir)
    tools.index_folder(str(first))
    tools.index_folder(str(second))

    result = tools.search_index("needle", root=str(second), limit=10)

    result_paths = {Path(item["path"]).name for item in result["results"]}
    assert result_paths == {"beta.txt"}


def test_apply_organization_plan_requires_confirmation(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    (root / "alpha.txt").write_text("alpha", encoding="utf-8")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    tools = FilePilotMCPTools(guard, plan_dir=tmp_path / "plans")
    plan = tools.propose_organization_plan(str(root), str(target), rules=["extension"])

    with pytest.raises(ValueError, match="confirm=True"):
        tools.apply_organization_plan(plan["plan_id"])

    assert (root / "alpha.txt").exists()


def test_apply_organization_plan_moves_files_when_confirmed(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    (root / "alpha.txt").write_text("alpha", encoding="utf-8")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    tools = FilePilotMCPTools(guard, plan_dir=tmp_path / "plans")
    plan = tools.propose_organization_plan(str(root), str(target), rules=["extension"])

    result = tools.apply_organization_plan(plan["plan_id"], confirm=True)

    assert result["moved"] == 1
    assert result["errors"] == 0
    assert not (root / "alpha.txt").exists()
    assert (target / "TXT" / "alpha.txt").exists()


def test_apply_organization_plan_keeps_partial_results_for_invalid_operation(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    (root / "alpha.txt").write_text("alpha", encoding="utf-8")
    plan_dir = tmp_path / "plans"
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    tools = FilePilotMCPTools(guard, plan_dir=plan_dir)
    plan = tools.propose_organization_plan(str(root), str(target), rules=["extension"])
    plan_path = plan_dir / f"{plan['plan_id']}.json"
    saved_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    saved_plan["operations"].append(
        {
            "source": str(tmp_path / "outside.txt"),
            "destination": str(target / "TXT" / "outside.txt"),
        }
    )
    plan_path.write_text(json.dumps(saved_plan), encoding="utf-8")

    result = tools.apply_organization_plan(plan["plan_id"], confirm=True)

    assert result["moved"] == 1
    assert result["errors"] == 1
    assert (target / "TXT" / "alpha.txt").exists()
    saved_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert len(saved_plan["applied_results"]) == 2
    assert [item["success"] for item in saved_plan["applied_results"]] == [True, False]


def test_undo_organization_plan_restores_moved_files(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    source = root / "alpha.txt"
    source.write_text("alpha", encoding="utf-8")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    tools = FilePilotMCPTools(guard, plan_dir=tmp_path / "plans")
    plan = tools.propose_organization_plan(str(root), str(target), rules=["extension"])
    tools.apply_organization_plan(plan["plan_id"], confirm=True)

    result = tools.undo_organization_plan(plan["plan_id"], confirm=True)

    assert result["restored"] == 1
    assert result["errors"] == 0
    assert source.exists()
    assert not (target / "TXT" / "alpha.txt").exists()


def test_undo_organization_plan_keeps_partial_results_for_invalid_operation(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    source = root / "alpha.txt"
    source.write_text("alpha", encoding="utf-8")
    plan_dir = tmp_path / "plans"
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    tools = FilePilotMCPTools(guard, plan_dir=plan_dir)
    plan = tools.propose_organization_plan(str(root), str(target), rules=["extension"])
    tools.apply_organization_plan(plan["plan_id"], confirm=True)
    plan_path = plan_dir / f"{plan['plan_id']}.json"
    saved_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    saved_plan["applied_results"].append(
        {
            "source": str(root / "outside.txt"),
            "destination": str(tmp_path / "outside.txt"),
            "success": True,
            "error": "",
        }
    )
    plan_path.write_text(json.dumps(saved_plan), encoding="utf-8")

    result = tools.undo_organization_plan(plan["plan_id"], confirm=True)

    assert result["restored"] == 1
    assert result["errors"] == 1
    assert source.exists()
    saved_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert len(saved_plan["undo_results"]) == 2
    assert sorted(item["success"] for item in saved_plan["undo_results"]) == [False, True]


def test_undo_organization_plan_requires_confirmation(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    (root / "alpha.txt").write_text("alpha", encoding="utf-8")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    tools = FilePilotMCPTools(guard, plan_dir=tmp_path / "plans")
    plan = tools.propose_organization_plan(str(root), str(target), rules=["extension"])
    tools.apply_organization_plan(plan["plan_id"], confirm=True)

    with pytest.raises(ValueError, match="confirm=True"):
        tools.undo_organization_plan(plan["plan_id"])


def test_list_plans_reports_status(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    (root / "alpha.txt").write_text("alpha", encoding="utf-8")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    tools = FilePilotMCPTools(guard, plan_dir=tmp_path / "plans")

    plan = tools.propose_organization_plan(str(root), str(target), rules=["extension"])
    listing = tools.list_plans()

    assert listing["count"] == 1
    entry = listing["plans"][0]
    assert entry["plan_id"] == plan["plan_id"]
    assert entry["status"] == "proposed"

    tools.apply_organization_plan(plan["plan_id"], confirm=True)
    listing_after = tools.list_plans()
    assert listing_after["plans"][0]["status"] == "applied"


def test_apply_organization_plan_rejects_double_apply(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    (root / "alpha.txt").write_text("alpha", encoding="utf-8")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    tools = FilePilotMCPTools(guard, plan_dir=tmp_path / "plans")
    plan = tools.propose_organization_plan(str(root), str(target), rules=["extension"])

    tools.apply_organization_plan(plan["plan_id"], confirm=True)

    with pytest.raises(ValueError, match="already applied"):
        tools.apply_organization_plan(plan["plan_id"], confirm=True)
