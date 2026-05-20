# Auto-Update

> Reference for FilePilot AI's built-in update checking system.

---

## Overview

FilePilot AI includes a threaded auto-update checker that queries GitHub Releases for new versions. It runs in the background and never blocks the UI.

**Source:** `filepilot/updater.py`

---

## How It Works

1. On startup, the app can call `check_async()` to spawn a background thread
2. The thread fetches the latest release from `https://github.com/cuiheng511/filepilot-ai/releases/latest`
3. Results are cached to `~/.filepilot/update_check_cache.json`
4. A callback notifies the UI when a new version is found

### Cache Behavior

| Result | Cache Duration |
|--------|---------------|
| Update available | 24 hours |
| No update | 24 hours |
| Network / API error | 1 hour (retry sooner) |

---

## API Reference

### Class: `UpdateChecker`

```python
from filepilot.updater import UpdateChecker, check_now
```

#### `check_async(callback=None)`

Run an update check in a background daemon thread.

| Parameter | Type | Description |
|-----------|------|-------------|
| `callback` | `Callable[[UpdateCheckResult], None]` | (Optional) Called with the result when the check completes |

**Returns:** `threading.Thread` — the background thread (already started).

**Example:**

```python
def on_result(result: UpdateCheckResult):
    if result.has_update:
        print(f"Update available: {result.release.version}")
        result.release.open_download_page()

checker = UpdateChecker()
thread = checker.check_async(callback=on_result)
```

#### `download(url, dest_path, progress_callback=None)`

Download a release asset to a local file with progress reporting.

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | `str` | Download URL from `ReleaseInfo.download_url` |
| `dest_path` | `str` or `Path` | Where to save the downloaded file |
| `progress_callback` | `Callable[[int], None]` | (Optional) Called with percentage (0–100) as bytes arrive |

**Returns:** `Path` — the downloaded file path.

**Raises:** `requests.RequestException` on HTTP or network failure.

**Example:**
```python
checker = UpdateChecker()
path = checker.download(release.download_url, "~/Downloads/FilePilot.exe")
```

#### `install(downloaded_path)`

Launch the platform-specific installer for a downloaded file.

| Parameter | Type | Description |
|-----------|------|-------------|
| `downloaded_path` | `str` or `Path` | Path to the downloaded installer file |

Platform behavior:
- **Windows** (`.exe`): launches with `/S` (silent) flag
- **macOS** (`.dmg`): opens with `open` command (user mounts manually)
- **Linux** (`.AppImage`): sets executable bit and launches

**Example:**
```python
checker = UpdateChecker()
checker.install("/tmp/FilePilot-AI-Setup-0.6.2.exe")
```

#### `open_download_page()`

Open the latest release page in the default web browser. Equivalent to navigating to the GitHub Releases page.

---

### Function: `check_now()`

Synchronous one-shot update check. Useful for testing or for pre-flight checks.

```python
from filepilot.updater import check_now

result = check_now()
if result.has_update:
    print(f"{result.release.version} is available")
    print(f"Published: {result.release.published_at}")
```

**Returns:** `UpdateCheckResult`

---

### Class: `UpdateCheckResult`

| Attribute | Type | Description |
|-----------|------|-------------|
| `has_update` | `bool` | Whether a newer version exists |
| `release` | `Release` | Details of the latest release (if available) |
| `error` | `str | None` | Error message if the check failed |

### Class: `Release`

| Attribute | Type | Description |
|-----------|------|-------------|
| `version` | `str` | Version tag (e.g. `"0.4.0"`) |
| `published_at` | `str` | ISO 8601 timestamp of the release |
| `html_url` | `str` | GitHub release page URL |

---

## Configuration

Update settings are stored in `~/.filepilot/settings.json`:

```json
{
  "update_check_enabled": true
}
```

The update checker uses the following internal constants:

| Constant | Value | Description |
|----------|-------|-------------|
| `CACHE_EXPIRY_HOURS` | 24 | Cache TTL for successful checks |
| `CACHE_EXPIRY_HOURS_ON_ERROR` | 1 | Retry interval after failed checks |
| `CACHE_FILE` | `~/.filepilot/update_check_cache.json` | Cache file path |
| `DOWNLOAD_BASE` | `https://github.com/cuiheng511/filepilot-ai/releases/latest` | Release URL |

---

## Troubleshooting

### Update check always returns no update

1. Check network connectivity — the checker needs access to `api.github.com`
2. Clear the cache file: `rm ~/.filepilot/update_check_cache.json`
3. Verify you're on the latest version locally: `python -c "from importlib.metadata import version; print(version('filepilot'))"`

### Update check fails with rate limit

GitHub API has a rate limit of 60 requests/hour for unauthenticated requests. The update check only runs once every 24 hours by default, so this is unlikely. If you hit the limit, the error is cached for 1 hour before retrying.

### Thread safety

The `UpdateChecker` is fully thread-safe. The background thread is a daemon thread, so it won't prevent the application from exiting.
