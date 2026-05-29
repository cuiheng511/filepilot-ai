from pathlib import Path

import pytest

from filepilot.mcp.audit import AuditLogger
from filepilot.mcp.security import MCPAccessError, MCPSecurityConfig, PathGuard
from filepilot.mcp.server import build_tools, parse_args
from filepilot.mcp.tools import FilePilotMCPTools


def test_audit_logger_writes_jsonl_records(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.record("add_tags", "success", path=tmp_path / "a.txt", details={"tags": ["work"]})

    records = logger.read_records()
    assert len(records) == 1
    assert records[0]["tool"] == "add_tags"
    assert records[0]["status"] == "success"
    assert records[0]["details"] == {"tags": ["work"]}


def test_add_tags_success_is_audited(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "workspace"
    root.mkdir()
    file_path = root / "note.txt"
    file_path.write_text("hello", encoding="utf-8")
    monkeypatch.setattr("filepilot.core.tag_manager.TAGS_FILE", tmp_path / "tags.json")
    logger = AuditLogger(tmp_path / "audit.jsonl")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root,), write_enabled=True))
    tools = FilePilotMCPTools(guard, audit_logger=logger)

    result = tools.add_tags(str(file_path), ["work", "notes"])

    assert result["tags"] == ["work", "notes"]
    records = logger.read_records()
    assert records[-1]["tool"] == "add_tags"
    assert records[-1]["status"] == "success"
    assert records[-1]["details"]["tags"] == ["work", "notes"]


def test_add_tags_denial_is_audited(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    file_path = root / "note.txt"
    file_path.write_text("hello", encoding="utf-8")
    logger = AuditLogger(tmp_path / "audit.jsonl")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root,), write_enabled=False))
    tools = FilePilotMCPTools(guard, audit_logger=logger)

    with pytest.raises(MCPAccessError):
        tools.add_tags(str(file_path), ["blocked"])

    records = logger.read_records()
    assert records[-1]["tool"] == "add_tags"
    assert records[-1]["status"] == "denied"
    assert "Write access is disabled" in records[-1]["error"]


def test_add_tags_outside_allowlist_is_audited_as_denied(tmp_path: Path):
    root = tmp_path / "workspace"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    file_path = outside / "note.txt"
    file_path.write_text("hello", encoding="utf-8")
    logger = AuditLogger(tmp_path / "audit.jsonl")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root,), write_enabled=True))
    tools = FilePilotMCPTools(guard, audit_logger=logger)

    with pytest.raises(MCPAccessError):
        tools.add_tags(str(file_path), ["blocked"])

    records = logger.read_records()
    assert records[-1]["tool"] == "add_tags"
    assert records[-1]["status"] == "denied"
    assert "outside allowed directories" in records[-1]["error"]


def test_build_tools_configures_audit_log(tmp_path: Path):
    allowed = tmp_path / "workspace"
    allowed.mkdir()
    audit_log = tmp_path / "custom-audit.jsonl"
    plan_dir = tmp_path / "plans"
    args = parse_args(
        ["--allow", str(allowed), "--audit-log", str(audit_log), "--plan-dir", str(plan_dir)]
    )

    tools = build_tools(args)

    status = tools.server_status()
    assert status["audit_log"] == str(audit_log)
    assert status["plan_dir"] == str(plan_dir)


def test_apply_organization_plan_denial_is_audited(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    (root / "note.txt").write_text("hello", encoding="utf-8")
    logger = AuditLogger(tmp_path / "audit.jsonl")
    plan_dir = tmp_path / "plans"

    write_guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    write_tools = FilePilotMCPTools(write_guard, plan_dir=plan_dir)
    plan = write_tools.propose_organization_plan(str(root), str(target), rules=["extension"])

    read_guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=False))
    read_tools = FilePilotMCPTools(read_guard, plan_dir=plan_dir, audit_logger=logger)
    with pytest.raises(ValueError, match="Write access is disabled"):
        read_tools.apply_organization_plan(plan["plan_id"], confirm=True)

    records = logger.read_records()
    assert records[-1]["tool"] == "apply_organization_plan"
    assert records[-1]["status"] == "denied"


def test_apply_organization_plan_confirmation_denial_is_audited(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    (root / "note.txt").write_text("hello", encoding="utf-8")
    logger = AuditLogger(tmp_path / "audit.jsonl")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    tools = FilePilotMCPTools(guard, plan_dir=tmp_path / "plans", audit_logger=logger)
    plan = tools.propose_organization_plan(str(root), str(target), rules=["extension"])

    with pytest.raises(ValueError, match="confirm=True"):
        tools.apply_organization_plan(plan["plan_id"])

    records = logger.read_records()
    assert records[-1]["tool"] == "apply_organization_plan"
    assert records[-1]["status"] == "denied"


def test_undo_organization_plan_success_is_audited(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    (root / "note.txt").write_text("hello", encoding="utf-8")
    logger = AuditLogger(tmp_path / "audit.jsonl")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    tools = FilePilotMCPTools(guard, plan_dir=tmp_path / "plans", audit_logger=logger)
    plan = tools.propose_organization_plan(str(root), str(target), rules=["extension"])
    tools.apply_organization_plan(plan["plan_id"], confirm=True)

    tools.undo_organization_plan(plan["plan_id"], confirm=True)

    records = logger.read_records()
    assert records[-1]["tool"] == "undo_organization_plan"
    assert records[-1]["status"] == "success"
    assert records[-1]["details"]["restored"] == 1


def test_undo_organization_plan_confirmation_denial_is_audited(tmp_path: Path):
    root = tmp_path / "workspace"
    target = tmp_path / "organized"
    root.mkdir()
    target.mkdir()
    (root / "note.txt").write_text("hello", encoding="utf-8")
    logger = AuditLogger(tmp_path / "audit.jsonl")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(root, target), write_enabled=True))
    tools = FilePilotMCPTools(guard, plan_dir=tmp_path / "plans", audit_logger=logger)
    plan = tools.propose_organization_plan(str(root), str(target), rules=["extension"])
    tools.apply_organization_plan(plan["plan_id"], confirm=True)

    with pytest.raises(ValueError, match="confirm=True"):
        tools.undo_organization_plan(plan["plan_id"])

    records = logger.read_records()
    assert records[-1]["tool"] == "undo_organization_plan"
    assert records[-1]["status"] == "denied"
