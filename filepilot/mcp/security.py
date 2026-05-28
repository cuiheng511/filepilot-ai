"""Directory-scoped safety checks for the FilePilot MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class MCPAccessError(ValueError):
    """Raised when an MCP request tries to access an unauthorized path."""


@dataclass(frozen=True)
class MCPSecurityConfig:
    """Security settings for local MCP access."""

    allowed_dirs: tuple[Path, ...]
    write_enabled: bool = False
    max_file_size_bytes: int = 50 * 1024 * 1024
    max_read_chars: int = 40_000
    allow_hidden: bool = False

    @classmethod
    def from_env(cls) -> MCPSecurityConfig:
        """Build config from environment variables.

        FILEPILOT_MCP_ALLOWED_DIRS uses the platform path separator:
        semicolon on Windows, colon on macOS/Linux.
        """
        raw_dirs = os.environ.get("FILEPILOT_MCP_ALLOWED_DIRS", "")
        dirs = [Path(p) for p in raw_dirs.split(os.pathsep) if p.strip()]

        write_enabled = os.environ.get("FILEPILOT_MCP_WRITE_ENABLED", "").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        max_file_mb = _read_positive_int("FILEPILOT_MCP_MAX_FILE_MB", 50)
        max_read_chars = _read_positive_int("FILEPILOT_MCP_MAX_READ_CHARS", 40_000)
        allow_hidden = os.environ.get("FILEPILOT_MCP_ALLOW_HIDDEN", "").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        return cls(
            allowed_dirs=tuple(dirs),
            write_enabled=write_enabled,
            max_file_size_bytes=max_file_mb * 1024 * 1024,
            max_read_chars=max_read_chars,
            allow_hidden=allow_hidden,
        )

    def normalized(self) -> MCPSecurityConfig:
        """Return a copy with absolute, existing allowed directories."""
        normalized_dirs: list[Path] = []
        for directory in self.allowed_dirs:
            resolved = directory.expanduser().resolve()
            if resolved.exists() and resolved.is_dir():
                normalized_dirs.append(resolved)
        return MCPSecurityConfig(
            allowed_dirs=tuple(dict.fromkeys(normalized_dirs)),
            write_enabled=self.write_enabled,
            max_file_size_bytes=self.max_file_size_bytes,
            max_read_chars=self.max_read_chars,
            allow_hidden=self.allow_hidden,
        )


class PathGuard:
    """Validate paths before exposing local files to an AI agent."""

    def __init__(self, config: MCPSecurityConfig):
        self.config = config.normalized()

    def list_allowed_dirs(self) -> list[str]:
        return [str(path) for path in self.config.allowed_dirs]

    def resolve_read_path(self, path: str | Path, *, allow_hidden: bool | None = None) -> Path:
        resolved = self._resolve(path)
        self._ensure_allowed(resolved)
        self._ensure_hidden_allowed(resolved, allow_hidden)
        return resolved

    def resolve_write_path(self, path: str | Path, *, allow_hidden: bool | None = None) -> Path:
        if not self.config.write_enabled:
            raise MCPAccessError("Write access is disabled. Restart with --write to allow changes.")
        resolved = self._resolve(path)
        self._ensure_allowed(resolved)
        self._ensure_hidden_allowed(resolved, allow_hidden)
        return resolved

    def ensure_file_readable(self, path: Path) -> None:
        if not path.exists():
            raise MCPAccessError(f"Path does not exist: {path}")
        if not path.is_file():
            raise MCPAccessError(f"Path is not a file: {path}")
        size = path.stat().st_size
        if size > self.config.max_file_size_bytes:
            raise MCPAccessError(
                f"File is too large ({size} bytes). Limit is {self.config.max_file_size_bytes} bytes."
            )

    def ensure_directory_readable(self, path: Path) -> None:
        if not path.exists():
            raise MCPAccessError(f"Path does not exist: {path}")
        if not path.is_dir():
            raise MCPAccessError(f"Path is not a directory: {path}")

    def is_allowed_path(self, path: str | Path) -> bool:
        try:
            self._ensure_allowed(self._resolve(path))
        except MCPAccessError:
            return False
        return True

    def _resolve(self, path: str | Path) -> Path:
        if not self.config.allowed_dirs:
            raise MCPAccessError(
                "No allowed directories configured. Start with --allow <directory>."
            )
        return Path(path).expanduser().resolve()

    def _ensure_allowed(self, path: Path) -> None:
        for root in self.config.allowed_dirs:
            if path == root or root in path.parents:
                return
        allowed = ", ".join(str(root) for root in self.config.allowed_dirs)
        raise MCPAccessError(f"Path is outside allowed directories: {path}. Allowed: {allowed}")

    def _ensure_hidden_allowed(self, path: Path, allow_hidden: bool | None) -> None:
        if allow_hidden if allow_hidden is not None else self.config.allow_hidden:
            return

        for root in self.config.allowed_dirs:
            try:
                relative = path.relative_to(root)
            except ValueError:
                continue
            if any(part.startswith(".") for part in relative.parts):
                raise MCPAccessError(
                    f"Hidden paths are disabled by default. Use --allow-hidden to access: {path}"
                )


def _read_positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default
