"""MCP server entry point for FilePilot AI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from filepilot.mcp.audit import AuditLogger
from filepilot.mcp.security import MCPSecurityConfig, PathGuard
from filepilot.mcp.tools import FilePilotMCPTools


def build_tools(args: argparse.Namespace) -> FilePilotMCPTools:
    allowed_dirs = tuple(Path(path) for path in args.allow)
    env_config = MCPSecurityConfig.from_env()
    config = MCPSecurityConfig(
        allowed_dirs=allowed_dirs or env_config.allowed_dirs,
        write_enabled=False if args.read_only else args.write or env_config.write_enabled,
        max_file_size_bytes=args.max_file_mb * 1024 * 1024,
        max_read_chars=args.max_read_chars,
        allow_hidden=args.allow_hidden or env_config.allow_hidden,
    )
    return FilePilotMCPTools(
        PathGuard(config),
        index_dir=args.index_dir,
        plan_dir=args.plan_dir,
        audit_logger=AuditLogger(args.audit_log),
    )


def create_server(tools: FilePilotMCPTools):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:
        raise RuntimeError(
            "The MCP SDK is not installed. Install with: pip install 'filepilot-ai[mcp]'"
        ) from e

    mcp = FastMCP("FilePilot AI")

    @mcp.tool()
    def server_status() -> dict:
        """Show allowed directories, write mode, and safety limits."""
        return tools.server_status()

    @mcp.tool()
    def list_workflow_templates(include_write: bool = True) -> dict:
        """List copy-paste-ready MCP workflow templates for agents."""
        return tools.list_workflow_templates(include_write)

    @mcp.tool()
    def get_workflow_template(template_id: str) -> dict:
        """Return one MCP workflow template with a full agent prompt."""
        return tools.get_workflow_template(template_id)

    @mcp.tool()
    def mcp_client_config(client: str = "generic", include_write: bool = False) -> dict:
        """Generate MCP client JSON using the current allowed roots."""
        return tools.mcp_client_config(client, include_write)

    @mcp.tool()
    def scan_files(
        root: str,
        recursive: bool = True,
        limit: int = 200,
        extensions: list[str] | None = None,
        include_hidden: bool = False,
    ) -> dict:
        """Scan local files under an allowed directory."""
        return tools.scan_files(root, recursive, limit, extensions, include_hidden)

    @mcp.tool()
    def search_files(
        root: str,
        query: str,
        recursive: bool = True,
        limit: int = 50,
        extensions: list[str] | None = None,
        include_hidden: bool = False,
    ) -> dict:
        """Search file names and relative paths without building an index."""
        return tools.search_files(root, query, recursive, limit, extensions, include_hidden)

    @mcp.tool()
    def index_folder(
        root: str,
        include_content: bool = True,
        recursive: bool = True,
        include_hidden: bool = False,
    ) -> dict:
        """Build or update the local FilePilot MCP search index."""
        return tools.index_folder(root, include_content, recursive, include_hidden)

    @mcp.tool()
    def search_index(
        query: str,
        root: str | None = None,
        limit: int = 50,
        semantic: bool = False,
    ) -> dict:
        """Search the FilePilot MCP index, optionally limited to a root directory."""
        return tools.search_index(query, root, limit, semantic)

    @mcp.tool()
    def read_file(path: str, start: int = 0, max_chars: int | None = None) -> dict:
        """Read a bounded text slice from an allowed local file."""
        return tools.read_file(path, start, max_chars)

    @mcp.tool()
    def extract_file_text(path: str, max_chars: int | None = None) -> dict:
        """Extract text from supported local document formats."""
        return tools.extract_file_text(path, max_chars)

    @mcp.tool()
    def summarize_file(path: str, max_length: int = 500) -> dict:
        """Summarize a local file with configured AI or a local fallback."""
        return tools.summarize_file(path, max_length)

    @mcp.tool()
    def suggest_tags(path: str, max_tags: int = 8) -> dict:
        """Suggest FilePilot tags for a local file without writing metadata."""
        return tools.suggest_tags(path, max_tags)

    @mcp.tool()
    def add_tags(path: str, tags: list[str]) -> dict:
        """Add FilePilot tag metadata. Requires --write."""
        return tools.add_tags(path, tags)

    @mcp.tool()
    def find_duplicates(
        root: str,
        min_size: int = 1,
        limit_groups: int = 50,
        include_hidden: bool = False,
    ) -> dict:
        """Find exact duplicate files under an allowed directory."""
        return tools.find_duplicates(root, min_size, limit_groups, include_hidden)

    @mcp.tool()
    def propose_organization_plan(
        root: str,
        target_root: str,
        rules: list[str] | None = None,
        rename_pattern: str | None = None,
        limit: int = 500,
        include_hidden: bool = False,
    ) -> dict:
        """Create a dry-run file organization plan. This never moves files."""
        return tools.propose_organization_plan(
            root,
            target_root,
            rules,
            rename_pattern,
            limit,
            include_hidden,
        )

    @mcp.tool()
    def list_plans(
        limit: int = 50,
        root: str | None = None,
        status: str | None = None,
        max_age_days: int | None = None,
    ) -> dict:
        """List saved organization plans and their applied/undone status."""
        return tools.list_plans(limit, root, status, max_age_days)

    @mcp.tool()
    def cleanup_plans(
        max_age_days: int = 30,
        status: str | None = None,
        dry_run: bool = True,
    ) -> dict:
        """Clean up old saved organization plans. Defaults to dry-run."""
        return tools.cleanup_plans(max_age_days, status, dry_run)

    @mcp.tool()
    def apply_organization_plan(plan_id: str, confirm: bool = False) -> dict:
        """Apply a saved organization plan. Requires --write and confirm=True."""
        return tools.apply_organization_plan(plan_id, confirm)

    @mcp.tool()
    def undo_organization_plan(plan_id: str, confirm: bool = False) -> dict:
        """Undo successful moves from an applied organization plan."""
        return tools.undo_organization_plan(plan_id, confirm)

    return mcp


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FilePilot AI as a local-first MCP server.")
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="DIR",
        help="Directory the MCP server may access. Repeat for multiple directories.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Allow MCP tools that write tag metadata or move files.",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Force read-only mode, overriding FILEPILOT_MCP_WRITE_ENABLED.",
    )
    parser.add_argument(
        "--allow-hidden",
        action="store_true",
        help="Allow access to dot-prefixed hidden paths inside allowed directories.",
    )
    parser.add_argument(
        "--max-file-mb", type=int, default=_env_int("FILEPILOT_MCP_MAX_FILE_MB", 50)
    )
    parser.add_argument(
        "--max-read-chars",
        type=int,
        default=_env_int("FILEPILOT_MCP_MAX_READ_CHARS", 40_000),
    )
    parser.add_argument(
        "--index-dir",
        default=os.environ.get(
            "FILEPILOT_MCP_INDEX_DIR", str(Path.home() / ".filepilot" / "mcp-index")
        ),
        help="Directory for the MCP search index.",
    )
    parser.add_argument(
        "--plan-dir",
        default=os.environ.get(
            "FILEPILOT_MCP_PLAN_DIR", str(Path.home() / ".filepilot" / "mcp-plans")
        ),
        help="Directory for saved MCP organization plans.",
    )
    parser.add_argument(
        "--audit-log",
        default=os.environ.get(
            "FILEPILOT_MCP_AUDIT_LOG", str(Path.home() / ".filepilot" / "mcp-audit.jsonl")
        ),
        help="JSONL audit log for MCP write operations.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    tools = build_tools(args)
    try:
        server = create_server(tools)
    except RuntimeError as e:
        sys.stderr.write(f"{e}\n")
        return 2
    server.run()
    return 0


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


if __name__ == "__main__":
    raise SystemExit(main())
