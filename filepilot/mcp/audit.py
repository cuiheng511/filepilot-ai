"""Append-only audit logging for FilePilot MCP write operations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    """Write JSONL audit records for MCP actions that mutate local metadata."""

    def __init__(self, log_path: str | Path | None = None):
        self.path = (
            Path(log_path).expanduser()
            if log_path
            else Path.home() / ".filepilot" / "mcp-audit.jsonl"
        )

    def record(
        self,
        tool: str,
        status: str,
        *,
        path: str | Path | None = None,
        details: dict[str, Any] | None = None,
        error: str = "",
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "status": status,
            "path": str(path) if path is not None else "",
            "details": details or {},
            "error": error,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def read_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        return records
