# MCP Client Setup

This guide shows ready-to-adapt configuration snippets for running FilePilot MCP from common agent clients. Exact configuration file locations can change between client releases, so use the JSON blocks as the source of truth for command and arguments.

## Recommended Defaults

Start read-only and allow only the folders the agent needs:

```bash
filepilot-mcp --allow ~/Documents --read-only
```

Read-only is the default. The explicit `--read-only` flag is recommended for shared agent configs because it overrides `FILEPILOT_MCP_WRITE_ENABLED` if that environment variable is present.

Enable writes only when you need `add_tags`, `apply_organization_plan`, or `undo_organization_plan`. For organization apply/undo, include both the source folder and target folder in `--allow`:

```bash
filepilot-mcp --allow ~/Documents --allow ~/Downloads --write
```

## Claude Desktop

```json
{
  "mcpServers": {
    "filepilot": {
      "command": "filepilot-mcp",
      "args": ["--allow", "C:\\Users\\you\\Documents", "--read-only"]
    }
  }
}
```

For a source checkout:

```json
{
  "mcpServers": {
    "filepilot": {
      "command": "python",
      "args": [
        "-m",
        "filepilot.mcp.server",
        "--allow",
        "C:\\Users\\you\\Documents",
        "--read-only"
      ]
    }
  }
}
```

## Claude Code

Claude Code accepts MCP servers as local commands. Use the same command and args shape:

```json
{
  "mcpServers": {
    "filepilot": {
      "command": "filepilot-mcp",
      "args": [
        "--allow",
        "/Users/you/Documents",
        "--allow",
        "/Users/you/Downloads",
        "--read-only"
      ]
    }
  }
}
```

## Cursor

Cursor MCP configuration also uses a server name with a command and args:

```json
{
  "mcpServers": {
    "filepilot": {
      "command": "filepilot-mcp",
      "args": [
        "--allow",
        "C:\\Users\\you\\Projects",
        "--max-read-chars",
        "30000",
        "--read-only"
      ]
    }
  }
}
```

## Codex

Use FilePilot MCP as a local stdio MCP server:

```json
{
  "mcpServers": {
    "filepilot": {
      "command": "filepilot-mcp",
      "args": [
        "--allow",
        "/home/you/Documents",
        "--read-only",
        "--audit-log",
        "/home/you/.filepilot/mcp-audit.jsonl"
      ]
    }
  }
}
```

## Write Mode Example

Use write mode only for trusted sessions:

```json
{
  "mcpServers": {
    "filepilot": {
      "command": "filepilot-mcp",
      "args": [
        "--allow",
        "C:\\Users\\you\\Downloads",
        "--allow",
        "C:\\Users\\you\\Sorted",
        "--write",
        "--audit-log",
        "C:\\Users\\you\\.filepilot\\mcp-audit.jsonl"
      ]
    }
  }
}
```

For organization workflows, ask the client to call `propose_organization_plan` first, review the returned operations, then use `list_plans` if it needs to rediscover the saved `plan_id` before applying or undoing a plan.

For stale plan metadata, ask the client to call `list_plans(root=..., status=..., max_age_days=...)`, then `cleanup_plans(max_age_days=..., dry_run=true)`. Repeat cleanup with `dry_run=false` only after reviewing the candidates and only in a trusted write-mode session.

## Prompt Patterns

```text
Use FilePilot in read-only mode to scan this folder, summarize file types and sizes, and do not move or tag anything.
```

```text
Use FilePilot to propose an organization plan for this folder, then show me the saved plan ID and operations. Do not apply it yet.
```

```text
Use FilePilot to list proposed plans for this root older than 30 days, run cleanup_plans as a dry-run, and explain what would be removed.
```

## Smoke Test

Before opening your client, verify the command works:

```bash
filepilot-mcp --help
```

For a source checkout:

```bash
python -m filepilot.mcp.server --help
```

If either command fails, reinstall with:

```bash
pip install -e ".[mcp]"
```
