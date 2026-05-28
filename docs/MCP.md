# FilePilot MCP Server

FilePilot MCP exposes FilePilot AI's local-first file tools to MCP clients such as Claude Code, Codex, Cursor, and other agent runtimes.

The server is designed to be conservative by default:

- It can only access directories passed with `--allow`.
- It starts in read-only mode.
- Hidden dot paths are blocked unless `--allow-hidden` is set.
- File reads are bounded by file size and returned characters.
- Organization is exposed as a dry-run plan, not an automatic move.

## Install

From a source checkout:

```bash
pip install -e ".[mcp]"
```

From a package install:

```bash
pip install "filepilot-ai[mcp]"
```

## Start The Server

Allow one directory:

```bash
filepilot-mcp --allow ~/Documents
```

Allow multiple directories:

```bash
filepilot-mcp --allow ~/Documents --allow ~/Downloads
```

Enable metadata writes for tools such as `add_tags`:

```bash
filepilot-mcp --allow ~/Documents --write
```

Tune read limits:

```bash
filepilot-mcp --allow ~/Documents --max-file-mb 25 --max-read-chars 20000
```

## Environment Variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `FILEPILOT_MCP_ALLOWED_DIRS` | Allowed directories, separated by the platform path separator. | Empty |
| `FILEPILOT_MCP_WRITE_ENABLED` | Set to `1`, `true`, `yes`, or `on` to allow write-like tools. | Disabled |
| `FILEPILOT_MCP_ALLOW_HIDDEN` | Set to `1`, `true`, `yes`, or `on` to allow dot-prefixed hidden paths. | Disabled |
| `FILEPILOT_MCP_MAX_FILE_MB` | Maximum readable file size in MB. | `50` |
| `FILEPILOT_MCP_MAX_READ_CHARS` | Maximum characters returned by read/extract tools. | `40000` |
| `FILEPILOT_MCP_INDEX_DIR` | Index directory used by MCP search tools. | `~/.filepilot/mcp-index` |

Command-line flags override defaults and are the recommended way to configure clients.

## Client Configuration

Most MCP clients accept a command and args list. Example:

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

For a source checkout, use Python directly if the console script is not on `PATH`:

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

## Tools

| Tool | Description | Write mode required |
| --- | --- | --- |
| `server_status` | Shows allowed directories, limits, write mode, and index location. | No |
| `scan_files` | Returns metadata for files under an allowed directory. | No |
| `search_files` | Searches file names and relative paths without building an index. | No |
| `index_folder` | Builds or updates a local FilePilot MCP index. | No |
| `search_index` | Searches the MCP index, optionally scoped to a root. | No |
| `read_file` | Reads a bounded text slice from a file. | No |
| `extract_file_text` | Extracts text from supported documents and code files. | No |
| `summarize_file` | Summarizes extracted text with configured AI or a local fallback. | No |
| `suggest_tags` | Suggests tags without writing metadata. | No |
| `add_tags` | Adds FilePilot tag metadata. | Yes |
| `find_duplicates` | Finds exact duplicate files under an allowed directory. | No |
| `propose_organization_plan` | Creates a dry-run organization plan. | No |

## Safety Notes

### Directory Scope

Every path is resolved before use and must be inside one of the configured allowed directories. Attempts to access sibling directories, parent directories, or unrelated absolute paths are rejected.

### Read Limits

`read_file` and `extract_file_text` enforce the configured maximum file size and returned character count. Agents receive a slice of content plus metadata showing whether the result was truncated.

### Writes

The first MCP release only enables tag metadata writes through `add_tags`, and only when `--write` is set. File moves, deletes, and renames remain planning-only through `propose_organization_plan`.

### Index Scope

The MCP server stores its own index under `~/.filepilot/mcp-index` by default. `search_index` filters results back through the current allowed directories, so stale results outside the current MCP scope are not returned.

## Suggested Agent Prompts

```text
Use FilePilot to scan my Downloads folder and find likely duplicate files.
```

```text
Use FilePilot to extract text from this PDF and summarize the main points.
```

```text
Use FilePilot to propose a safe organization plan for my screenshots folder, but do not move anything.
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `The MCP SDK is not installed` | Install with `pip install "filepilot-ai[mcp]"` or `pip install -e ".[mcp]"`. |
| `No allowed directories configured` | Add at least one `--allow <directory>` argument. |
| `Path is outside allowed directories` | Pass a path inside one of the allowed roots or add another allowed root. |
| Hidden path rejected | Restart with `--allow-hidden` if you intentionally need dot-prefixed paths. |
| Index search returns nothing | Run `index_folder` on an allowed directory first. |
