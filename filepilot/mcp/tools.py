"""Tool implementation shared by the MCP server and tests."""

from __future__ import annotations

import json
import secrets
import shutil
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from filepilot.ai.summarizer import Summarizer
from filepilot.core.duplicate_finder import DuplicateFinder
from filepilot.core.file_organizer import (
    CategoryRule,
    DateRule,
    ExtensionRule,
    FileOrganizer,
    OrganizeRule,
    SizeRule,
)
from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.core.indexer import FileIndexer
from filepilot.core.tag_manager import TagManager
from filepilot.mcp.audit import AuditLogger
from filepilot.mcp.security import MCPAccessError, PathGuard
from filepilot.mcp.workflows import build_client_config, get_template, list_templates


class FilePilotMCPTools:
    """Local-first FilePilot operations exposed through MCP."""

    def __init__(
        self,
        guard: PathGuard,
        index_dir: str | Path | None = None,
        plan_dir: str | Path | None = None,
        audit_logger: AuditLogger | None = None,
    ):
        self.guard = guard
        self.index_dir = (
            Path(index_dir).expanduser() if index_dir else Path.home() / ".filepilot" / "mcp-index"
        )
        self.plan_dir = (
            Path(plan_dir).expanduser() if plan_dir else Path.home() / ".filepilot" / "mcp-plans"
        )
        self.audit_logger = audit_logger
        self._indexer: FileIndexer | None = None

    def _get_indexer(self) -> FileIndexer:
        """Return a cached FileIndexer, opening the Whoosh index only once.

        Reusing the indexer avoids re-opening the index and reloading the
        embedding cache on every index/search call.
        """
        if self._indexer is None:
            self._indexer = FileIndexer(index_dir=self.index_dir)
        return self._indexer

    def server_status(self) -> dict:
        """Return the server's safety posture and configured directories."""
        return {
            "allowed_dirs": self.guard.list_allowed_dirs(),
            "write_enabled": self.guard.config.write_enabled,
            "allow_hidden": self.guard.config.allow_hidden,
            "max_file_size_bytes": self.guard.config.max_file_size_bytes,
            "max_read_chars": self.guard.config.max_read_chars,
            "index_dir": str(self.index_dir),
            "plan_dir": str(self.plan_dir),
            "audit_log": str(self.audit_logger.path) if self.audit_logger else "",
        }

    def list_workflow_templates(self, include_write: bool = True) -> dict:
        """List ready-to-use agent workflow templates."""
        templates = list_templates(include_write=include_write)
        return {"count": len(templates), "templates": templates}

    def get_workflow_template(self, template_id: str) -> dict:
        """Return one agent workflow template with the full prompt."""
        return get_template(template_id)

    def mcp_client_config(self, client: str = "generic", include_write: bool = False) -> dict:
        """Generate a copy-paste-ready client config from the current allowed roots."""
        allowed_dirs = self.guard.list_allowed_dirs()
        return build_client_config(
            client,
            allowed_dirs,
            read_only=not include_write,
            include_write=include_write,
        )

    def scan_files(
        self,
        root: str,
        recursive: bool = True,
        limit: int = 200,
        extensions: list[str] | None = None,
        include_hidden: bool = False,
    ) -> dict:
        """Scan an allowed directory and return file metadata."""
        root_path = self.guard.resolve_read_path(root, allow_hidden=include_hidden)
        self.guard.ensure_directory_readable(root_path)

        normalized_exts = _normalize_extensions(extensions)
        scanner = FileScanner()
        files = scanner.scan(root_path, recursive=recursive, include_hidden=include_hidden)
        if normalized_exts:
            files = [f for f in files if f.extension in normalized_exts]
        files = files[: max(1, min(limit, 1000))]

        return {
            "root": str(root_path),
            "count": len(files),
            "files": [_file_info_to_dict(f, root_path) for f in files],
            "stats": scanner.stats,
        }

    def search_files(
        self,
        root: str,
        query: str,
        recursive: bool = True,
        limit: int = 50,
        extensions: list[str] | None = None,
        include_hidden: bool = False,
    ) -> dict:
        """Search file names and paths inside an allowed directory without building an index."""
        root_path = self.guard.resolve_read_path(root, allow_hidden=include_hidden)
        self.guard.ensure_directory_readable(root_path)

        query_lower = query.lower().strip()
        normalized_exts = _normalize_extensions(extensions)
        scanner = FileScanner()
        matches: list[FileInfo] = []
        for file_info in scanner.scan(
            root_path, recursive=recursive, include_hidden=include_hidden
        ):
            if normalized_exts and file_info.extension not in normalized_exts:
                continue
            relative = file_info.relative_path(root_path).lower()
            if query_lower in file_info.name.lower() or query_lower in relative:
                matches.append(file_info)
            if len(matches) >= max(1, min(limit, 200)):
                break

        return {
            "root": str(root_path),
            "query": query,
            "count": len(matches),
            "results": [_file_info_to_dict(f, root_path) for f in matches],
        }

    def index_folder(
        self,
        root: str,
        include_content: bool = True,
        recursive: bool = True,
        include_hidden: bool = False,
    ) -> dict:
        """Build or update a path-scoped local search index."""
        root_path = self.guard.resolve_read_path(root, allow_hidden=include_hidden)
        self.guard.ensure_directory_readable(root_path)

        scanner = FileScanner()
        files = scanner.scan(root_path, recursive=recursive, include_hidden=include_hidden)
        indexer = self._get_indexer()
        indexed = indexer.index_files(
            files,
            content_extractor=self._extract_for_index if include_content else None,
            incremental=True,
        )
        return {
            "root": str(root_path),
            "scanned": len(files),
            "indexed": indexed,
            "include_content": include_content,
            "index_stats": indexer.get_stats(),
        }

    def search_index(
        self,
        query: str,
        root: str | None = None,
        limit: int = 50,
        semantic: bool = False,
    ) -> dict:
        """Search the FilePilot MCP index, optionally scoped to an allowed directory."""
        root_path = None
        if root:
            root_path = self.guard.resolve_read_path(root)
            self.guard.ensure_directory_readable(root_path)

        indexer = self._get_indexer()
        raw_results = (
            indexer.search_semantic(query, limit=limit * 2)
            if semantic
            else indexer.search(query, limit=limit * 2)
        )
        results = []
        for result in raw_results:
            path = Path(result["path"]).resolve()
            if not self.guard.is_allowed_path(path):
                continue
            if root_path and not (path == root_path or root_path in path.parents):
                continue
            results.append(result)
            if len(results) >= max(1, min(limit, 200)):
                break

        return {"query": query, "count": len(results), "results": results}

    def read_file(self, path: str, start: int = 0, max_chars: int | None = None) -> dict:
        """Read a slice from a text file inside an allowed directory.

        Reads only the bytes needed (start + read_limit) plus a small margin to
        determine truncation, instead of loading the whole file into memory.
        """
        file_path = self.guard.resolve_read_path(path)
        self.guard.ensure_file_readable(file_path)
        read_limit = self._read_limit(max_chars)
        start = max(0, start)

        # Read only up to what we need (+1 char to detect truncation).
        # errors="replace" keeps decoding robust for non-UTF8 bytes.
        want = start + read_limit
        with file_path.open(encoding="utf-8", errors="replace") as handle:
            head = handle.read(want + 1)
            has_more = bool(handle.read(1))

        chunk = head[start : start + read_limit]
        truncated = has_more or (len(head) > start + len(chunk))
        return {
            "path": str(file_path),
            "name": file_path.name,
            "start": start,
            "returned_chars": len(chunk),
            "total_chars": None,  # not computed to avoid full-file read
            "truncated": truncated,
            "content": chunk,
        }

    def extract_file_text(self, path: str, max_chars: int | None = None) -> dict:
        """Extract text from documents, code, Markdown, spreadsheets, and presentations."""
        file_path = self.guard.resolve_read_path(path)
        self.guard.ensure_file_readable(file_path)
        read_limit = self._read_limit(max_chars)

        text = extract_text(file_path)
        return {
            "path": str(file_path),
            "name": file_path.name,
            "extension": file_path.suffix.lower(),
            "returned_chars": min(len(text), read_limit),
            "total_chars": len(text),
            "truncated": len(text) > read_limit,
            "content": text[:read_limit],
        }

    def summarize_file(self, path: str, max_length: int = 500) -> dict:
        """Summarize a file with configured AI, falling back to an extractive local summary."""
        file_path = self.guard.resolve_read_path(path)
        self.guard.ensure_file_readable(file_path)
        text = extract_text(file_path)
        if not text.strip():
            return {
                "path": str(file_path),
                "success": False,
                "summary": "",
                "keywords": [],
                "error": "No extractable text",
            }

        summarizer = Summarizer()
        max_length = max(80, min(max_length, 2000))
        summary = summarizer.summarize_text(text[:8000], max_length=max_length)
        source = "ai"
        if not summary:
            summary = _extractive_summary(text, max_length)
            source = "local-extractive"

        return {
            "path": str(file_path),
            "success": True,
            "summary": summary,
            "summary_source": source,
            "keywords": summarizer.extract_keywords(text, top_n=10),
        }

    def suggest_tags(self, path: str, max_tags: int = 8) -> dict:
        """Suggest tags for a file without writing tag metadata."""
        file_path = self.guard.resolve_read_path(path)
        self.guard.ensure_file_readable(file_path)
        text = extract_text(file_path)
        summarizer = Summarizer()
        keywords = (
            summarizer.extract_keywords(text, top_n=max(1, min(max_tags, 20))) if text else []
        )
        category = FileScanner.create_file_info(file_path).category.label
        tags = []
        for tag in [category, file_path.suffix.lower().lstrip("."), *keywords]:
            if tag and tag not in tags:
                tags.append(tag)
        return {"path": str(file_path), "suggested_tags": tags[:max_tags]}

    def add_tags(self, path: str, tags: list[str]) -> dict:
        """Write FilePilot tag metadata. Requires write mode."""
        cleaned_tags = [tag.strip() for tag in tags if tag.strip()]
        try:
            file_path = self.guard.resolve_write_path(path)
            self.guard.ensure_file_exists(file_path)
            manager = TagManager()
            for tag in cleaned_tags:
                manager.add_tag(file_path, tag)
            manager.flush()
            result = {"path": str(file_path), "tags": manager.get_tags(file_path)}
            self._audit(
                "add_tags",
                "success",
                path=file_path,
                details={"tags": cleaned_tags, "tag_count": len(result["tags"])},
            )
            return result
        except Exception as e:
            self._audit(
                "add_tags",
                self._audit_failure_status(e),
                path=path,
                details={"tags": cleaned_tags},
                error=str(e),
            )
            raise

    def find_duplicates(
        self,
        root: str,
        min_size: int = 1,
        limit_groups: int = 50,
        include_hidden: bool = False,
    ) -> dict:
        """Find exact duplicate files inside an allowed directory."""
        root_path = self.guard.resolve_read_path(root, allow_hidden=include_hidden)
        self.guard.ensure_directory_readable(root_path)

        scanner = FileScanner()
        files = scanner.scan(root_path, include_hidden=include_hidden)
        finder = DuplicateFinder()
        groups = finder.find_duplicates(files, min_size=max(1, min_size))
        limited = groups[: max(1, min(limit_groups, 200))]
        stats = finder.get_duplicate_stats(groups)
        return {
            "root": str(root_path),
            "groups_returned": len(limited),
            "groups_total": len(groups),
            "stats": stats,
            "duplicates": [
                {
                    "size_bytes": group[0].size_bytes,
                    "size": group[0].size_str,
                    "files": [str(file_info.path) for file_info in group],
                }
                for group in limited
            ],
        }

    def propose_organization_plan(
        self,
        root: str,
        target_root: str,
        rules: list[str] | None = None,
        rename_pattern: str | None = None,
        limit: int = 500,
        include_hidden: bool = False,
    ) -> dict:
        """Create a dry-run organization plan. This never moves files."""
        root_path = self.guard.resolve_read_path(root, allow_hidden=include_hidden)
        self.guard.ensure_directory_readable(root_path)

        target = Path(target_root).expanduser().resolve()
        # Note: target is intentionally NOT validated against the allowlist here.
        # propose is a pure dry-run; apply_organization_plan re-validates every
        # source and destination against the current allowlist before moving.
        scanner = FileScanner()
        files = scanner.scan(root_path, include_hidden=include_hidden)[: max(1, min(limit, 2000))]
        organizer = FileOrganizer()
        operations = organizer.organize(
            files,
            target_root=target,
            rules=_rules_from_names(rules),
            dry_run=True,
            rename=bool(rename_pattern),
            rename_pattern=rename_pattern,
        )
        target_slots = _target_slots_from_operations(operations)
        plan_id = self._save_plan(root_path, target, operations, target_slots=target_slots)
        return {
            "plan_id": plan_id,
            "root": str(root_path),
            "target_root": str(target),
            "count": len(operations),
            "dry_run": True,
            "target_slots": target_slots,
            "operations": operations,
        }

    def apply_organization_plan(self, plan_id: str, confirm: bool = False) -> dict:
        """Apply a previously generated organization plan.

        Requires write mode and an explicit confirm=True flag. Sources and
        destinations are re-validated against the current allowlist before any
        move happens.
        """
        if not confirm:
            error = "apply_organization_plan requires confirm=True"
            self._audit(
                "apply_organization_plan",
                "denied",
                details={"plan_id": plan_id},
                error=error,
            )
            raise ValueError(error)

        try:
            if not self.guard.config.write_enabled:
                raise ValueError("Write access is disabled. Restart with --write to allow changes.")
            plan = self._load_plan(plan_id)
            if plan.get("applied_at"):
                raise ValueError(
                    f"Plan {plan_id} was already applied at {plan['applied_at']}. "
                    "Create a new plan to organize again."
                )
            operations = list(plan.get("operations", []))
            results = []
            moved = 0
            errors = 0

            for operation in operations:
                source_value = str(operation.get("source", ""))
                destination_value = str(operation.get("destination", ""))
                source_output = source_value
                destination_output = destination_value
                try:
                    source = self.guard.resolve_write_path(source_value)
                    destination = self.guard.resolve_write_path(destination_value)
                    source_output = str(source)
                    destination_output = str(destination)
                    self.guard.ensure_file_exists(source)
                    if destination.exists():
                        raise FileExistsError(f"Destination already exists: {destination}")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source), str(destination))
                    moved += 1
                    results.append(
                        {
                            "source": str(source),
                            "destination": str(destination),
                            "success": True,
                            "error": "",
                        }
                    )
                except Exception as e:
                    errors += 1
                    results.append(
                        {
                            "source": source_output,
                            "destination": destination_output,
                            "success": False,
                            "error": str(e),
                        }
                    )

            self._save_applied_plan(plan, results)
            self._audit(
                "apply_organization_plan",
                "success" if errors == 0 else "partial",
                path=plan.get("root", ""),
                details={"plan_id": plan_id, "moved": moved, "errors": errors},
            )
            return {
                "plan_id": plan_id,
                "moved": moved,
                "errors": errors,
                "results": results,
            }
        except Exception as e:
            self._audit(
                "apply_organization_plan",
                self._audit_failure_status(e),
                details={"plan_id": plan_id},
                error=str(e),
            )
            raise

    def undo_organization_plan(self, plan_id: str, confirm: bool = False) -> dict:
        """Undo successful moves from a previously applied organization plan."""
        if not confirm:
            error = "undo_organization_plan requires confirm=True"
            self._audit(
                "undo_organization_plan",
                "denied",
                details={"plan_id": plan_id},
                error=error,
            )
            raise ValueError(error)

        try:
            if not self.guard.config.write_enabled:
                raise ValueError("Write access is disabled. Restart with --write to allow changes.")
            plan = self._load_plan(plan_id)
            if plan.get("undone_at"):
                raise ValueError(f"Plan {plan_id} was already undone at {plan['undone_at']}.")
            applied_results = list(plan.get("applied_results", []))
            if not applied_results:
                raise ValueError(f"Organization plan has no successful applied moves: {plan_id}")

            restored = 0
            errors = 0
            results = []
            for operation in reversed(applied_results):
                if not operation.get("success"):
                    continue
                source_value = str(operation.get("source", ""))
                destination_value = str(operation.get("destination", ""))
                source_output = source_value
                destination_output = destination_value
                try:
                    source = self.guard.resolve_write_path(source_value)
                    destination = self.guard.resolve_write_path(destination_value)
                    source_output = str(source)
                    destination_output = str(destination)
                    self.guard.ensure_file_exists(destination)
                    if source.exists():
                        raise FileExistsError(f"Original source already exists: {source}")
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(destination), str(source))
                    restored += 1
                    results.append(
                        {
                            "source": str(source),
                            "destination": str(destination),
                            "success": True,
                            "error": "",
                        }
                    )
                except Exception as e:
                    errors += 1
                    results.append(
                        {
                            "source": source_output,
                            "destination": destination_output,
                            "success": False,
                            "error": str(e),
                        }
                    )

            plan["undo_results"] = results
            plan["undone_at"] = datetime.now(timezone.utc).isoformat()
            self._write_plan(plan_id, plan)
            self._audit(
                "undo_organization_plan",
                "success" if errors == 0 else "partial",
                path=plan.get("root", ""),
                details={"plan_id": plan_id, "restored": restored, "errors": errors},
            )
            return {
                "plan_id": plan_id,
                "restored": restored,
                "errors": errors,
                "results": results,
            }
        except Exception as e:
            self._audit(
                "undo_organization_plan",
                self._audit_failure_status(e),
                details={"plan_id": plan_id},
                error=str(e),
            )
            raise

    def list_plans(
        self,
        limit: int = 50,
        root: str | None = None,
        status: str | None = None,
        max_age_days: int | None = None,
    ) -> dict:
        """List saved organization plans with their status.

        Helps an agent discover plan IDs created by propose_organization_plan
        and check whether each has been applied or undone.
        """
        root_path = self.guard.resolve_read_path(root) if root else None
        normalized_status = _normalize_plan_status(status)
        max_age_days = _normalize_max_age_days(max_age_days)
        plans: list[dict] = []
        if self.plan_dir.exists():
            plan_files = sorted(
                self.plan_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for plan_file in plan_files:
                try:
                    data = json.loads(plan_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not self._plan_visible(data):
                    continue
                plan_status = "proposed"
                if data.get("undone_at"):
                    plan_status = "undone"
                elif data.get("applied_at"):
                    plan_status = "applied"
                if normalized_status and plan_status != normalized_status:
                    continue
                if root_path and not _plan_matches_root(data, root_path):
                    continue
                plan = self._plan_summary(data, plan_file, plan_status, max_age_days)
                plans.append(plan)
                if len(plans) >= max(1, min(limit, 200)):
                    break
        return {
            "count": len(plans),
            "filters": {
                "root": str(root_path) if root_path else "",
                "status": normalized_status or "",
                "max_age_days": max_age_days,
            },
            "plans": plans,
        }

    def cleanup_plans(
        self,
        max_age_days: int = 30,
        status: str | None = None,
        dry_run: bool = True,
    ) -> dict:
        """Remove old saved organization plans from the MCP plan directory.

        Defaults to dry-run so agents can show exactly what would be removed
        before mutating FilePilot's internal plan metadata.
        """
        normalized_max_age_days = _normalize_max_age_days(max_age_days)
        max_age_days = 30 if normalized_max_age_days is None else normalized_max_age_days
        normalized_status = _normalize_plan_status(status)
        if not dry_run and not self.guard.config.write_enabled:
            error = "Write access is disabled. Restart with --write to remove saved plans."
            self._audit(
                "cleanup_plans",
                "denied",
                details={"max_age_days": max_age_days, "status": normalized_status or ""},
                error=error,
            )
            raise ValueError(error)
        removed = 0
        candidates = []
        try:
            if self.plan_dir.exists():
                for plan_file in sorted(self.plan_dir.glob("*.json")):
                    try:
                        data = json.loads(plan_file.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue
                    if not self._plan_visible(data):
                        continue
                    plan_status = "proposed"
                    if data.get("undone_at"):
                        plan_status = "undone"
                    elif data.get("applied_at"):
                        plan_status = "applied"
                    if normalized_status and plan_status != normalized_status:
                        continue
                    summary = self._plan_summary(data, plan_file, plan_status, max_age_days)
                    if not summary["expired"]:
                        continue
                    candidates.append(summary)
                    if not dry_run:
                        plan_file.unlink()
                        removed += 1
            if not dry_run:
                self._audit(
                    "cleanup_plans",
                    "success",
                    path=self.plan_dir,
                    details={
                        "max_age_days": max_age_days,
                        "status": normalized_status or "",
                        "removed": removed,
                    },
                )
        except Exception as e:
            if not dry_run:
                self._audit(
                    "cleanup_plans",
                    self._audit_failure_status(e),
                    path=self.plan_dir,
                    details={"max_age_days": max_age_days, "status": normalized_status or ""},
                    error=str(e),
                )
            raise
        return {
            "dry_run": dry_run,
            "max_age_days": max_age_days,
            "status": normalized_status or "",
            "candidates": candidates,
            "candidate_count": len(candidates),
            "removed": removed,
        }

    def _plan_visible(self, plan: dict) -> bool:
        root = plan.get("root", "")
        return bool(root and self.guard.is_allowed_path(root))

    def _plan_summary(
        self,
        plan: dict,
        plan_file: Path,
        status: str,
        max_age_days: int | None,
    ) -> dict:
        age_days = _plan_age_days(plan, plan_file)
        expired = bool(
            max_age_days is not None and age_days is not None and age_days > max_age_days
        )
        return {
            "plan_id": plan.get("plan_id", plan_file.stem),
            "status": status,
            "root": plan.get("root", ""),
            "target_root": plan.get("target_root", ""),
            "operation_count": len(plan.get("operations", [])),
            "target_slot_count": len(plan.get("target_slots", [])),
            "target_slots": list(plan.get("target_slots", []))[:10],
            "created_at": plan.get("created_at", ""),
            "applied_at": plan.get("applied_at", ""),
            "undone_at": plan.get("undone_at", ""),
            "age_days": age_days,
            "expired": expired,
        }

    def _extract_for_index(self, file_info: FileInfo) -> str:
        try:
            self.guard.ensure_file_readable(file_info.path)
            return extract_text(file_info.path)[: self.guard.config.max_read_chars]
        except Exception:
            return ""

    def _read_limit(self, max_chars: int | None) -> int:
        if max_chars is None:
            return self.guard.config.max_read_chars
        return max(1, min(max_chars, self.guard.config.max_read_chars))

    def _audit(
        self,
        tool: str,
        status: str,
        *,
        path: str | Path | None = None,
        details: dict | None = None,
        error: str = "",
    ) -> None:
        if self.audit_logger is None:
            return
        self.audit_logger.record(tool, status, path=path, details=details, error=error)

    def _audit_failure_status(self, error: Exception) -> str:
        if isinstance(error, MCPAccessError) or not self.guard.config.write_enabled:
            return "denied"
        return "error"

    def _save_plan(
        self,
        root: Path,
        target: Path,
        operations: list[dict],
        *,
        target_slots: list[dict] | None = None,
    ) -> str:
        self.plan_dir.mkdir(parents=True, exist_ok=True)
        plan_id = secrets.token_hex(12)
        plan = {
            "plan_id": plan_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "root": str(root),
            "target_root": str(target),
            "target_slots": target_slots or _target_slots_from_operations(operations),
            "operations": operations,
        }
        self._plan_path(plan_id).write_text(
            json.dumps(plan, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return plan_id

    def _save_applied_plan(self, plan: dict, results: list[dict]) -> None:
        plan_id = str(plan["plan_id"])
        plan["applied_results"] = results
        plan["applied_at"] = datetime.now(timezone.utc).isoformat()
        self._write_plan(plan_id, plan)

    def _write_plan(self, plan_id: str, plan: dict) -> None:
        self._plan_path(plan_id).write_text(
            json.dumps(plan, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_plan(self, plan_id: str) -> dict:
        if not _is_safe_plan_id(plan_id):
            raise ValueError(f"Invalid plan id: {plan_id}")
        plan_path = self._plan_path(plan_id)
        if not plan_path.exists():
            raise FileNotFoundError(f"Organization plan not found: {plan_id}")
        return cast(dict, json.loads(plan_path.read_text(encoding="utf-8")))

    def _plan_path(self, plan_id: str) -> Path:
        return self.plan_dir / f"{plan_id}.json"


def extract_text(file_path: Path) -> str:
    """Extract text from supported files, falling back to UTF-8 text reads.

    Delegates to the shared extraction dispatch in
    ``filepilot.extractors.text_extraction``.
    """
    from filepilot.extractors.text_extraction import extract_text as _shared_extract

    return _shared_extract(file_path)


def _rules_from_names(names: Iterable[str] | None) -> list[OrganizeRule]:
    rule_map: dict[str, Callable[[], OrganizeRule]] = {
        "category": CategoryRule,
        "type": CategoryRule,
        "date": DateRule,
        "extension": ExtensionRule,
        "size": SizeRule,
    }
    selected = []
    for name in names or ["category"]:
        rule_class = rule_map.get(name.lower())
        if rule_class:
            selected.append(rule_class())
    return selected or [CategoryRule()]


def _target_slots_from_operations(operations: list[dict]) -> list[dict]:
    slots: dict[str, dict] = {}
    for operation in operations:
        slot_id = str(operation.get("target_slot") or "").strip()
        if not slot_id:
            continue
        slot = slots.setdefault(
            slot_id,
            {
                "slot_id": slot_id,
                "target_dir": str(operation.get("target_dir") or ""),
                "target_subdir": str(operation.get("target_subdir") or "."),
                "operation_count": 0,
            },
        )
        slot["operation_count"] += 1
    return sorted(slots.values(), key=lambda item: item["slot_id"])


def _file_info_to_dict(file_info: FileInfo, root: Path | None = None) -> dict:
    return {
        "path": str(file_info.path),
        "relative_path": file_info.relative_path(root),
        "name": file_info.name,
        "extension": file_info.extension,
        "category": file_info.category.label,
        "size_bytes": file_info.size_bytes,
        "size": file_info.size_str,
        "modified": file_info.modified_time.isoformat(),
        "created": file_info.created_time.isoformat(),
        "mime_type": file_info.mime_type,
    }


def _normalize_extensions(extensions: list[str] | None) -> set[str]:
    if not extensions:
        return set()
    return {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}


def _extractive_summary(text: str, max_length: int) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary = " ".join(lines)
    if len(summary) <= max_length:
        return summary
    return summary[: max_length - 3].rstrip() + "..."


def _is_safe_plan_id(plan_id: str) -> bool:
    return bool(plan_id) and all(ch in "0123456789abcdef" for ch in plan_id) and len(plan_id) <= 64


def _normalize_plan_status(status: str | None) -> str | None:
    if status is None or not status.strip():
        return None
    normalized = status.strip().lower()
    if normalized not in {"proposed", "applied", "undone"}:
        raise ValueError("Plan status must be one of: proposed, applied, undone")
    return normalized


def _normalize_max_age_days(max_age_days: int | None) -> int | None:
    if max_age_days is None:
        return None
    return max(0, min(int(max_age_days), 3650))


def _plan_age_days(plan: dict, plan_file: Path) -> int | None:
    raw_created = str(plan.get("created_at", ""))
    created_at = _parse_datetime(raw_created)
    if created_at is None:
        try:
            created_at = datetime.fromtimestamp(plan_file.stat().st_mtime, timezone.utc)
        except OSError:
            return None
    now = datetime.now(timezone.utc)
    return max(0, (now - created_at).days)


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _plan_matches_root(plan: dict, root: Path) -> bool:
    for raw_path in (plan.get("root", ""), plan.get("target_root", "")):
        if not raw_path:
            continue
        try:
            path = Path(raw_path).expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        if path == root or root in path.parents:
            return True
    return False
