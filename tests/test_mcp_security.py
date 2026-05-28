from pathlib import Path

import pytest

from filepilot.mcp.security import MCPAccessError, MCPSecurityConfig, PathGuard


def test_path_guard_allows_paths_inside_allowed_dir(tmp_path: Path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    file_path = allowed / "note.txt"
    file_path.write_text("hello", encoding="utf-8")

    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(allowed,)))

    assert guard.resolve_read_path(file_path) == file_path.resolve()


def test_path_guard_rejects_paths_outside_allowed_dir(tmp_path: Path):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    outside_file = outside / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")

    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(allowed,)))

    with pytest.raises(MCPAccessError):
        guard.resolve_read_path(outside_file)


def test_path_guard_rejects_hidden_paths_by_default(tmp_path: Path):
    hidden_dir = tmp_path / ".hidden"
    hidden_dir.mkdir()
    hidden_file = hidden_dir / "note.txt"
    hidden_file.write_text("hello", encoding="utf-8")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(tmp_path,)))

    with pytest.raises(MCPAccessError):
        guard.resolve_read_path(hidden_file)


def test_path_guard_write_requires_explicit_mode(tmp_path: Path):
    file_path = tmp_path / "note.txt"
    file_path.write_text("hello", encoding="utf-8")
    guard = PathGuard(MCPSecurityConfig(allowed_dirs=(tmp_path,), write_enabled=False))

    with pytest.raises(MCPAccessError):
        guard.resolve_write_path(file_path)
