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
