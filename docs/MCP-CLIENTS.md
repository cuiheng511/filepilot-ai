# MCP Client Setup

This guide shows ready-to-adapt configuration snippets for running FilePilot MCP from common agent clients. Exact configuration file locations can change between client releases, so use the JSON blocks as the source of truth for command and arguments.

## Recommended Defaults

Start read-only and allow only the folders the agent needs:

```bash
filepilot-mcp --allow ~/Documents
```

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
      "args": ["--allow", "C:\\Users\\you\\Documents"]
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
        "C:\\Users\\you\\Documents"
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
        "/Users/you/Downloads"
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
        "30000"
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
