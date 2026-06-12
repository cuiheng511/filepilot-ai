# Promotion Kit

This page collects copy, links, and checklist items for submitting FilePilot AI
to open-source directories, awesome lists, newsletters, MCP lists, and community
threads.

## Canonical Links

| Item | Link |
| --- | --- |
| Repository | `https://github.com/cuiheng511/filepilot-ai` |
| README | `https://github.com/cuiheng511/filepilot-ai#readme` |
| MCP guide | `https://github.com/cuiheng511/filepilot-ai/blob/main/docs/MCP.md` |
| MCP clients | `https://github.com/cuiheng511/filepilot-ai/blob/main/docs/MCP-CLIENTS.md` |
| MCP workflows | `https://github.com/cuiheng511/filepilot-ai/blob/main/docs/MCP-WORKFLOWS.md` |
| Architecture | `https://github.com/cuiheng511/filepilot-ai/blob/main/docs/ARCHITECTURE.md` |
| Roadmap | `https://github.com/cuiheng511/filepilot-ai/blob/main/docs/ROADMAP.md` |
| Releases | `https://github.com/cuiheng511/filepilot-ai/releases` |

## One-Line Descriptions

Use one of these depending on the submission context:

- FilePilot AI is a local-first file manager with a desktop app, CLI, and safe MCP server for AI coding agents.
- Local-first MCP tools for searching, summarizing, tagging, deduplicating, and organizing your own files.
- A privacy-first Python/PySide6 file intelligence app that gives Claude Code, Codex, Cursor, and other agents scoped access to local files.
- A desktop + CLI + MCP project for preview-first file organization, duplicate review, and bounded local document understanding.

## Short Pitch

FilePilot AI is a local-first file intelligence project for people who want
better search, previews, summaries, duplicate review, and organization without
handing an AI agent unrestricted filesystem access. It ships as a desktop app,
a CLI, and an MCP server. The MCP server is read-only by default, scoped to
explicit `--allow` roots, and uses bounded reads, dry-run organization plans,
confirmation gates, and audit logs for write-like actions.

## Longer Pitch

FilePilot AI sits between local files and the tools that need to inspect them.
It can scan folders, index file metadata and text, extract content from common
document formats, find duplicate files, tag files, and propose organization
plans before anything moves. The same core services power a PySide6 desktop app,
a scriptable CLI, and an MCP server for Claude Code, Codex, Cursor, Claude
Desktop, and other agent clients.

The project is designed around conservative defaults: files stay local, AI is
optional, MCP tools only see explicitly allowed directories, write-like actions
require `--write`, and organization changes are saved as reviewable plans before
they can be applied. This makes it useful both as an end-user file tool and as a
practical open-source reference for building safer local agent integrations.

## Suggested GitHub Repository Metadata

Repository description:

```text
Local-first file intelligence: desktop app, CLI, and safe MCP server for AI agents.
```

Suggested topics:

```text
file-manager
file-organization
local-first
mcp
mcp-server
model-context-protocol
ai-agents
claude-code
codex
cursor
desktop-app
pyside6
duplicate-detection
semantic-search
privacy-first
```

## Submission Categories

Good fits:

- MCP server lists and Model Context Protocol resource collections.
- AI agent tooling directories.
- Local-first software lists.
- Python desktop application showcases.
- Open-source productivity tools.
- File management and document workflow lists.
- Privacy-first AI tools.

Less ideal fits:

- Cloud SaaS directories.
- Pure LLM prompt collections.
- Agent benchmarks with no local-tooling category.
- Destructive cleanup tool lists that expect automatic deletion.

## Submission Checklist

Before submitting to an external list:

- Confirm the latest `main` CI run is green.
- Confirm README first screen shows the logo, badges, demo, and quick pitch.
- Confirm the latest GitHub Release is published and marked as latest.
- Confirm screenshots render in README.
- Confirm `docs/MCP.md`, `docs/MCP-CLIENTS.md`, and `docs/MCP-WORKFLOWS.md` match the current tool list.
- Confirm the repository description and topics are set on GitHub.
- Choose the shortest pitch that matches the target list's style.
- Link to the MCP docs when submitting to agent or MCP directories.
- Link to screenshots or release assets when submitting to desktop app lists.

## Example Awesome List Entry

```markdown
- [FilePilot AI](https://github.com/cuiheng511/filepilot-ai) - Local-first file intelligence app with a desktop UI, CLI, and scoped MCP server for AI agents.
```

## Example MCP Directory Entry

```markdown
### FilePilot AI

Local-first MCP server for scoped file search, extraction, summaries, duplicate
review, tagging, and dry-run organization plans. Read-only by default; write-like
tools require explicit `--write`, confirmation, allowlisted roots, and audit logs.

Repository: https://github.com/cuiheng511/filepilot-ai
Docs: https://github.com/cuiheng511/filepilot-ai/blob/main/docs/MCP.md
```

## Example Launch Post

```text
I built FilePilot AI, a local-first file intelligence app for desktop users and AI coding agents.

It combines:
- PySide6 desktop file workflows
- CLI scanning/search/duplicates/organization
- MCP tools for Claude Code, Codex, Cursor, and Claude Desktop

The MCP server is scoped to explicit folders, read-only by default, and uses bounded reads, dry-run organization plans, confirmation gates, and audit logs for write-like actions.

Repo: https://github.com/cuiheng511/filepilot-ai
```

## Example Maintainer Reply

```text
Thanks for taking a look. The main difference is that FilePilot is not just an MCP demo: it also has a desktop app, CLI, tests, release packaging, and a conservative safety model around local files. The MCP server is read-only by default and only exposes folders passed with --allow.
```

## Recommended Next Outreach Targets

Start with small, high-fit targets:

1. MCP server directories and GitHub lists.
2. AI coding agent tooling lists.
3. Local-first and privacy-first software lists.
4. Python/PySide6 desktop showcases.
5. Productivity and file-management newsletters or weekly roundups.

Avoid posting everywhere at once. A better first wave is three to five relevant
places, then use feedback to tighten the README and examples.
