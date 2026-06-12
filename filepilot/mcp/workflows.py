"""Agent workflow templates and client config helpers for FilePilot MCP."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

WORKFLOW_TEMPLATES: tuple[dict, ...] = (
    {
        "id": "safe_inventory",
        "title": "Safe folder inventory",
        "mode": "read-only",
        "requires_write": False,
        "tools": ["server_status", "scan_files", "search_files"],
        "description": "Map a folder, identify important file groups, and report next steps.",
        "prompt": (
            "Use FilePilot MCP in read-only mode. First call server_status and confirm the "
            "allowed roots. Then scan the target folder with scan_files, summarize file counts "
            "by category and extension, and call out large or unusual files. Do not move, tag, "
            "or delete anything."
        ),
    },
    {
        "id": "document_brief",
        "title": "Local document brief",
        "mode": "read-only",
        "requires_write": False,
        "tools": ["server_status", "search_files", "extract_file_text", "summarize_file"],
        "description": "Find and summarize local documents without broad filesystem access.",
        "prompt": (
            "Use FilePilot MCP in read-only mode. Confirm allowed roots with server_status. "
            "Search only inside those roots, extract text from the relevant documents, and "
            "summarize findings with file paths and caveats. Keep excerpts short and do not "
            "write metadata."
        ),
    },
    {
        "id": "duplicate_review",
        "title": "Duplicate review",
        "mode": "read-only",
        "requires_write": False,
        "tools": ["server_status", "find_duplicates"],
        "description": "Group duplicate files for human review before any cleanup.",
        "prompt": (
            "Use FilePilot MCP in read-only mode. Confirm scope with server_status, then run "
            "find_duplicates on the requested root. Report duplicate groups, total wasted size "
            "when available, and recommend review order. Do not delete files."
        ),
    },
    {
        "id": "organization_plan",
        "title": "Preview-first organization plan",
        "mode": "read-only-first",
        "requires_write": False,
        "tools": ["server_status", "propose_organization_plan", "list_plans"],
        "description": "Create a saved dry-run organization plan for review.",
        "prompt": (
            "Use FilePilot MCP to create a dry-run organization plan only. Confirm both source "
            "and target roots are allowed, call propose_organization_plan, then show the plan_id, "
            "operation count, sample moves, and risks. Do not apply the plan unless the user later "
            "starts a trusted write-mode session and explicitly approves confirm=true."
        ),
    },
    {
        "id": "apply_reviewed_plan",
        "title": "Apply a reviewed organization plan",
        "mode": "write-after-review",
        "requires_write": True,
        "tools": ["server_status", "list_plans", "apply_organization_plan"],
        "description": "Apply a saved plan only after explicit review and confirmation.",
        "prompt": (
            "Use FilePilot MCP in write mode only after the user has reviewed the saved plan. "
            "Call server_status, verify write_enabled is true, rediscover the plan with list_plans, "
            "confirm source and target roots are allowed, and call apply_organization_plan with "
            "confirm=true only for the exact approved plan_id. Report successes and failures."
        ),
    },
    {
        "id": "plan_metadata_cleanup",
        "title": "Plan metadata cleanup",
        "mode": "dry-run-first",
        "requires_write": True,
        "tools": ["list_plans", "cleanup_plans"],
        "description": "Preview and remove stale FilePilot plan metadata without touching user files.",
        "prompt": (
            "Use list_plans to inspect saved organization plans. Call cleanup_plans with dry_run=true "
            "first and show the candidate plan IDs, statuses, and ages. Only repeat cleanup_plans "
            "with dry_run=false in a write-mode session after explicit user approval. This removes "
            "plan metadata only, not user files."
        ),
    },
)


CLIENT_ALIASES = {
    "claude": "claude_desktop",
    "claude-desktop": "claude_desktop",
    "claude_desktop": "claude_desktop",
    "claude-code": "claude_code",
    "claude_code": "claude_code",
    "cursor": "cursor",
    "codex": "codex",
    "generic": "generic",
}


def list_templates(include_write: bool = True) -> list[dict]:
    """Return workflow template summaries."""
    templates = (
        WORKFLOW_TEMPLATES
        if include_write
        else tuple(item for item in WORKFLOW_TEMPLATES if not item["requires_write"])
    )
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "mode": item["mode"],
            "requires_write": item["requires_write"],
            "tools": list(item["tools"]),
            "description": item["description"],
        }
        for item in templates
    ]


def get_template(template_id: str) -> dict:
    """Return one workflow template by id."""
    normalized = template_id.strip().lower().replace("-", "_")
    for item in WORKFLOW_TEMPLATES:
        if item["id"] == normalized:
            return deepcopy(item)
    valid = ", ".join(item["id"] for item in WORKFLOW_TEMPLATES)
    raise ValueError(f"Unknown workflow template: {template_id}. Valid templates: {valid}")


def build_client_config(
    client: str,
    allowed_dirs: list[str],
    *,
    read_only: bool = True,
    include_write: bool = False,
) -> dict:
    """Build a copy-paste-ready MCP client config using the current allowed roots."""
    client_key = CLIENT_ALIASES.get(client.strip().lower(), "generic")
    args = []
    for path in allowed_dirs:
        args.extend(["--allow", path])
    if include_write:
        args.append("--write")
    elif read_only:
        args.append("--read-only")

    server_block = {"command": "filepilot-mcp", "args": args}
    config = {"mcpServers": {"filepilot": server_block}}
    if client_key == "claude_desktop":
        location = "Claude Desktop MCP settings JSON"
    elif client_key == "claude_code":
        location = "Claude Code MCP configuration"
    elif client_key == "cursor":
        location = "Cursor MCP configuration"
    elif client_key == "codex":
        location = "Codex MCP configuration"
    else:
        location = "Generic MCP client configuration"
    return {
        "client": client_key,
        "location": location,
        "config": config,
        "safety_notes": [
            "The generated config uses only the roots already allowed for this MCP session.",
            "Read-only mode is recommended for shared or persistent client configs.",
            "Use write mode only for trusted sessions after reviewing a dry-run plan.",
        ],
    }


def normalize_allowed_dirs(raw_dirs: list[str]) -> list[str]:
    """Normalize allowed root strings for display in generated configs."""
    return [str(Path(path).expanduser()) for path in raw_dirs if path]
