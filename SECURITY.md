# Security Policy

FilePilot AI is local-first software that can scan, index, summarize, tag,
deduplicate, and organize local files. Security reports should focus on behavior
that could expose, modify, move, or delete user files outside the intended
boundaries.

## Supported Versions

Security fixes target the latest release on `main`. Older local builds should be
updated before reporting behavior that may already be fixed.

## Reporting A Vulnerability

Please open a private security advisory on GitHub if available. If that is not
available, create an issue with minimal detail and ask for a private disclosure
channel. Do not post private file contents, API keys, access tokens, or full
local paths in a public issue.

Useful information:

- FilePilot version or commit SHA.
- Operating system and Python version.
- Whether the issue affects desktop, CLI, MCP, or plugin behavior.
- Exact command-line flags for MCP issues, with private paths redacted.
- A minimal reproduction using temporary files when possible.

## MCP Safety Expectations

MCP reports are especially useful when they show one of these failures:

- Access outside explicit `--allow` roots.
- Hidden paths returned without `--allow-hidden`.
- Write-like behavior without `--write`.
- Organization apply/undo without `confirm=true`.
- Missing audit records for write-like MCP operations.
- Overwriting existing files without explicit handling.

## Non-Security Issues

General bugs, packaging failures, feature requests, and documentation issues
should use the public issue templates.
