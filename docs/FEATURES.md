# Feature Guide

Practical notes for newer FilePilot AI workflows.

## AI Chat

The AI Chat panel answers natural-language questions about indexed files.

- Simple queries such as "How many files do I have?", "Find large files", or "Show Python files" use local intent parsing.
- More open-ended prompts can use the configured AI provider.
- Build or update the index first for the most useful answers.

## Plugin Registry

The Plugin Manager can browse registry entries and install extractor plugins.

- Remote registry plugins require a SHA-256 pin.
- Plugin names are restricted to safe filename characters.
- Installed plugins are local Python code, so only install plugins from trusted sources.
- Custom plugins can still be placed in the local plugin directory for development.

## Organize Workflow Precheck

The Organize panel presents file organization as a visible workflow:

1. Select a source and target.
2. Scan and preview planned moves.
3. Review the safety precheck.
4. Execute only after the precheck passes and the user confirms.
5. Use the undo entry when the latest move needs to be restored.

Use **Add Source** to merge more than one source folder into a single organize
run. FilePilot scans the selected roots together, then applies one shared
preview, precheck, execute, history, and undo flow.

The precheck flags missing absolute source paths, existing target paths,
duplicate target destinations, cross-drive moves, and files routed into the
`Review` folder.

Preview rows include stable target slots such as `D001` for destination
directories, so users and agents can discuss a plan without copying long paths.
The precheck summary and organize history also include target slot counts.

Unknown-category files can be routed into `Review` so the main organization run
can still proceed while ambiguous files remain easy to inspect.

Successful runs append a local JSONL history record under `~/.filepilot/`, and
the panel shows the latest moved/error/review counts.

## Tag Cloud

The Tags panel includes a Tag Cloud view.

- Larger labels mean the tag appears on more files.
- Clicking a tag filters the tag list.
- The cloud reflows with the panel size and is rebuilt from the current tag database.

## Live Regex Preview

The Organize panel shows rename previews as you type regex patterns and replacements.

- Preview before executing bulk rename operations.
- Undo data is captured for rename runs.
- Rename templates that include `{ext}` do not append the extension twice.

## Notification History

The Notifications panel records recent toast messages.

- Use it to review background scan, update, indexing, and file-operation messages.
- The list is capped to avoid unbounded memory growth.
- Clear the list when you no longer need the history.

## Accessibility and Themes

- Newer panels expose accessible names for primary inputs, buttons, message bubbles, and notification lists.
- FilePilot ships dark, light, and high-contrast QSS themes. Setting `theme` to `high_contrast` in the app settings applies the high-contrast stylesheet.
- Keyboard shortcuts remain available for panel navigation and theme toggling.

## Embedding Cache Maintenance

Settings includes embedding cache controls.

- Refresh stats to inspect entry count and storage size.
- Remove missing files to prune cache rows for files no longer on disk.
- Compact cache after large cleanup runs.
