# Roadmap

This roadmap is a working direction for FilePilot AI. It is intentionally
practical: the project favors safer local file workflows, maintainable code, and
agent-ready integrations over broad feature sprawl.

## Current Focus

FilePilot AI is in a beta-quality phase with three stable surfaces:

- Desktop app for visual file workflows.
- CLI for repeatable local automation.
- MCP server for Claude Code, Codex, Cursor, and other AI coding agents.

Recent releases focused on MCP safety, release quality, coverage guardrails, CI
stability, a stronger first-run desktop experience, and built-in MCP workflow
templates. The next work should continue improving reliability and developer
confidence before adding large new product areas.

Version 0.8.1 started the desktop organization polish pass: the Organize panel
now has a visible workflow pipeline, execution precheck, Review routing for
unknown files, and a recent local history summary.

## Near-Term Priorities

| Priority | Goal | Why it matters |
| --- | --- | --- |
| Coverage lift | Raise total coverage from the high 60s toward 75% and then 80%. | Keeps the growing desktop and MCP surfaces from regressing. |
| Widget test depth | Add focused tests for `file_stats_panel.py`, `search_panel.py`, and selected file-browser workflows. | These are user-visible areas with many branches. |
| MCP integration test | Add a true MCP client/server smoke path beyond tool registration. | Confirms agent clients can call the server end to end. |
| Desktop polish | Improve empty states, status surfaces, and onboarding follow-through. | Helps new users understand what to do next without reading docs first. |
| Architecture docs | Keep high-level architecture and contribution docs current. | Makes the project easier for new contributors and AI agents to navigate. |
| Release polish | Continue improving artifact naming, checksums, and updater compatibility. | Makes desktop releases easier to trust and install. |

## 0.6.x Quality Track

The remaining 0.6.x releases should stay small and boring:

- Add tests around high-value, low-risk modules.
- Fix dead code and misleading UI messages.
- Improve docs and examples.
- Keep CI green across the full matrix.
- Avoid large UI rewrites unless they remove clear risk.

Good candidates:

- More `chat_assistant.py` and local intent parsing tests.
- `file_stats_panel.py` statistics and empty-state tests.
- `task_scheduler.py` and `task_queue.py` branch tests.
- `plugin_registry.py` cache, network-error, and validation tests.
- MCP docs examples for common agent workflows.

## 0.7.x Direction

Version 0.7 started the product-polish track with first-run onboarding, dashboard
workspace status, and clearer security/privacy settings. The remaining 0.7.x
work should deepen that experience without opening large new product areas.

Potential themes:

- Better onboarding follow-through after a folder is opened.
- Clearer desktop status surfaces for index, cache, and background tasks.
- Stronger MCP end-to-end validation.
- A more structured plugin registry workflow.
- Improved release packaging and updater verification.

## 0.8.x Direction

Version 0.8 started MCP productization with built-in workflow templates, a
client config helper, and stronger GitHub contributor surfaces. The remaining
0.8.x work should make those flows easier to verify end to end.

- End-to-end MCP client/server integration tests.
- More example transcripts showing agents using workflow templates correctly.
- Better observability for plan metadata, audit logs, and scoped roots.
- Better desktop visibility for organize plans, precheck results, history, and undo.
- Label synchronization and curated good-first-issue triage.

## 0.9 Direction

Version 0.9 should focus on desktop confidence:

- More polished empty states after onboarding.
- File stats and search panel coverage lift.
- Better release artifact verification summaries.
- Optional screenshots or short demo capture for the README.
- Optional folder icon workbench or folder-label polish after core organize safety is stable.

## Larger Refactors

Some modules are large enough that refactors should be planned separately:

- `file_browser.py` is a major UI surface and should not be split casually.
- Search panel behavior should be covered before deep restructuring.
- Any move-related refactor should preserve preview, overwrite refusal, and undo behavior.
- MCP safety code should remain small, explicit, and heavily tested.

When refactoring, prefer one boundary at a time: extract a helper, add tests,
then move behavior. Avoid combining refactors with feature work.

## Non-Goals

FilePilot should not become:

- A cloud-first file manager.
- A background sync service.
- A destructive cleanup tool that acts without preview.
- An agent tool that exposes the whole filesystem by default.
- A plugin marketplace that installs unsigned or unpinned remote code.

These constraints are part of the product identity, not temporary limitations.

## Contribution Ideas

Good first contributions:

- Add extractor tests for real-world edge cases.
- Improve documentation examples.
- Add empty-state tests for UI panels.
- Expand CLI help text and examples.
- Add MCP prompt examples for safe agent workflows.

Higher-impact contributions:

- End-to-end MCP client tests.
- Improved release asset verification.
- More resilient updater tests.
- Coverage improvements for large desktop panels.
- Architecture-preserving extraction of reusable UI helpers.

## Release Checklist For Future Work

Before cutting a release:

- Run `pre-commit run --all-files`.
- Run the full test suite with coverage.
- Confirm coverage stays above the configured baseline.
- Verify release notes are accurate and not overstated.
- Check that desktop assets include direct installer files and checksum sidecars.
- Confirm MCP docs match the actual tool list and safety behavior.
