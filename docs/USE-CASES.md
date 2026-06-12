# Use Cases

FilePilot AI is built for practical local file workflows. It can be used as a
desktop file manager, a repeatable CLI tool, or a scoped MCP server for AI
coding agents.

## 1. Triage A Messy Downloads Folder

Downloads folders accumulate installers, screenshots, PDFs, archives, exports,
and one-off files. FilePilot helps turn that pile into a reviewed plan.

Typical workflow:

1. Scan `~/Downloads` in the desktop app or CLI.
2. Review file categories, sizes, and modified dates.
3. Preview an organization plan by category, extension, or date.
4. Apply only after reviewing the planned moves.
5. Use undo data if a move needs to be rolled back.

Why FilePilot fits:

- Organization starts as a preview.
- Existing destinations are not overwritten blindly.
- Desktop users can review moves visually.
- CLI users can script dry-run plans before applying them.

## 2. Find And Review Duplicate Files

Duplicate cleanup is risky when tools only show a delete button. FilePilot
focuses on grouping and review first.

Typical workflow:

1. Scan a project export, photo folder, or backup directory.
2. Group files by duplicate content.
3. Review paths, sizes, and duplicate sets.
4. Send unwanted copies to the system recycle bin instead of permanently deleting them.

Why FilePilot fits:

- Duplicate groups use hashing rather than filename guesses.
- The desktop UI keeps duplicate sets inspectable.
- Safe deletion uses `send2trash`.
- CLI duplicate reports can be used in scripted audits.

## 3. Summarize Local Documents Without Giving Up Control

FilePilot can extract text from common document formats and summarize them with
local or configured cloud AI providers.

Typical workflow:

1. Drop files into the Summary panel or scan a folder.
2. Extract text from PDF, DOCX, XLSX, PPTX, Markdown, code, or plain text.
3. Use local AI when privacy matters, or a configured cloud provider when desired.
4. Keep file management local even when summaries are AI-assisted.

Why FilePilot fits:

- AI is optional.
- Local models are supported through Ollama, llama.cpp, vLLM, and LM Studio style endpoints.
- Cloud providers are explicit configuration choices.
- Basic scanning, search, duplicates, tags, and organization work without AI.

## 4. Give Coding Agents Scoped Local File Access

AI coding agents are useful, but broad filesystem access is uncomfortable.
FilePilot MCP provides useful local file tools behind explicit boundaries.

Typical workflow:

1. Start the server with one or more allowed roots:

   ```bash
   filepilot-mcp --allow ~/Documents --read-only
   ```

2. Let the agent scan, search, index, extract, or summarize files inside those roots.
3. Keep write-like tools disabled by default.
4. For organization tasks, ask the agent to create a dry-run plan first.
5. Restart with `--write` only for trusted sessions that need tagging, apply, or undo.

Why FilePilot fits:

- Paths are resolved and checked against allowed roots.
- Read size and returned text are bounded.
- Hidden dot paths are blocked unless explicitly enabled.
- Organization plans require review and confirmation.
- Write-like MCP actions are audited.

## 5. Maintain An Open Source Project

FilePilot itself uses the same quality habits it encourages: scoped tools,
coverage guardrails, release checklists, and documentation that AI agents can
understand.

Typical workflow:

1. Use the CLI to inventory release artifacts.
2. Use MCP tools to let an agent inspect docs or project files without broad access.
3. Run pre-commit hooks before pushing.
4. Use CI coverage reports to spot regressions.
5. Keep release notes and updater behavior aligned.

Why FilePilot fits:

- The repository has a documented architecture and roadmap.
- MCP docs make agent behavior easier to review.
- Release assets include checksums for installers.
- Coverage and CI checks make maintenance less guessy.

## 6. Add Support For New File Types

FilePilot has an extractor plugin model for adding structured text extraction.

Typical workflow:

1. Create a custom extractor plugin.
2. Implement support for a new file type or domain-specific format.
3. Place it in the local plugin directory for development.
4. Share registry entries only with safe names and SHA-256 pins.

Why FilePilot fits:

- Extractors isolate file-type specific logic.
- The plugin SDK documents discovery, integration, and best practices.
- Registry plugins require pinned hashes before installation.
- Users stay in control of local code execution.

## Choosing The Right Surface

| Need | Best surface |
| --- | --- |
| Browse files visually | Desktop app |
| Run repeatable scans or exports | CLI |
| Let an AI agent inspect local files safely | MCP server |
| Add support for a new file type | Extractor plugin |
| Prepare a reviewed organization plan | Desktop app, CLI, or MCP |
| Build local-first file intelligence workflows | Core services |

## Good Prompts For Agent Workflows

```text
Use FilePilot in read-only mode to scan this folder, summarize file types and sizes, and do not move or tag anything.
```

```text
Use FilePilot to find duplicate files under this export folder. Group exact duplicates by content and show the paths. Do not delete anything.
```

```text
Use FilePilot to propose an organization plan for this folder by extension and date. Save the plan, show the operations, and wait for approval before applying it.
```

```text
Use FilePilot to extract text from these PDFs and summarize the main differences. Keep each extraction bounded.
```

```text
Use FilePilot to list old saved organization plans for this root and run cleanup_plans as a dry-run only.
```

## What FilePilot Avoids

FilePilot is intentionally conservative:

- It does not upload your filesystem index to a hosted service.
- It does not give agents unrestricted filesystem access.
- It does not silently apply destructive organization actions.
- It does not install remote plugins without pinned hashes.
- It does not require AI for ordinary file management.

That restraint is the point: the project is useful because it makes local file
intelligence safer to use repeatedly.
