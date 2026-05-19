"""Auto-update checker for FilePilot AI.

Checks GitHub Releases for newer versions in the background.
Integrated into SettingsDialog and main window.

Usage:
    from filepilot.updater import UpdateChecker

    checker = UpdateChecker()
    checker.check_async(callback=on_update_available)
"""

from __future__ import annotations

import json
import logging
import platform
import subprocess
import sys
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Thread

import requests

from filepilot import __version__

logger = logging.getLogger(__name__)

# ── Constants ──

GITHUB_REPO = "cuiheng511/filepilot-ai"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CHECK_CACHE_FILE = "~/.filepilot/update_check_cache.json"
CACHE_EXPIRY_HOURS = 24
CACHE_EXPIRY_HOURS_ON_ERROR = 1  # Retry sooner if last check failed
DOWNLOAD_BASE = f"https://github.com/{GITHUB_REPO}/releases/latest"


# ── Data ──


@dataclass
class ReleaseInfo:
    """Information about a GitHub release."""

    version: str
    title: str
    body: str
    published_at: str
    html_url: str
    download_url: str | None
    download_size: int = 0


@dataclass
class UpdateCheckResult:
    """Result of an update check."""

    has_update: bool
    current_version: str
    release: ReleaseInfo | None = None
    error: str | None = None
    checked_at: float = field(default_factory=time.time)


# ── Update Checker ──


class UpdateChecker:
    """Checks for new FilePilot AI releases on GitHub."""

    def __init__(self) -> None:
        self._latest_result: UpdateCheckResult | None = None
        self._cache_dir = Path(CHECK_CACHE_FILE).expanduser().parent
        self._cache_file = Path(CHECK_CACHE_FILE).expanduser()

    # ── Public API ──

    @property
    def latest_result(self) -> UpdateCheckResult | None:
        """Most recent check result (or None if never checked)."""
        return self._latest_result

    def check(self) -> UpdateCheckResult:
        """Synchronously check for updates.

        Returns:
            UpdateCheckResult with has_update, release info, or error.
        """
        # Try cache first (shorter expiry for errors)
        cached = self._load_cache()
        if cached is not None:
            # Don't use cached errors
            if not cached.error:
                self._latest_result = cached
                return cached
            # Only use cached errors for a shorter period
            if self.cache_age_hours < CACHE_EXPIRY_HOURS_ON_ERROR:
                self._latest_result = cached
                return cached

        result = self._fetch_release()
        self._latest_result = result
        self._save_cache(result)
        return result

    def check_async(self, callback: Callable[[UpdateCheckResult], None] | None = None) -> Thread:
        """Check for updates in a background thread.

        ⚠️ The callback runs on a background thread.
        If it updates Qt UI, use QTimer.singleShot(0, ...) to dispatch
        to the main thread, or emit a Qt Signal instead.

        Args:
            callback: Optional function to call with the result when done.
                Called from a background thread — be thread-safe!

        Returns:
            The background Thread object (already started).
        """
        thread = Thread(target=self._check_thread, args=(callback,), daemon=True)
        thread.start()
        return thread

    def open_download_page(self) -> None:
        """Open the latest release page in the default browser."""
        webbrowser.open(DOWNLOAD_BASE)

    def download(
        self,
        url: str,
        dest_path: str | Path,
        progress_callback: Callable[[int], None] | None = None,
    ) -> Path:
        """Download a release asset to a local path with progress reporting.

        Args:
            url: Download URL.
            dest_path: Where to save the file.
            progress_callback: Called with bytes downloaded so far.

        Returns:
            Path to the downloaded file.

        Raises:
            requests.RequestException on failure.
        """
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(int(downloaded / total * 100))
        return dest

    def install(self, downloaded_path: str | Path) -> None:
        """Launch the installer for the downloaded file.

        Platform-specific behavior:
          - Windows (.exe): run silently with ``/S``.
          - macOS (.dmg): open the DMG (user mounts manually).
          - Linux (.AppImage): ``chmod +x`` and run.

        Args:
            downloaded_path: Path to the downloaded installer.
        """
        path = Path(downloaded_path)
        name = path.name.lower()
        current_platform = str(sys.platform)

        if current_platform.startswith("win") and name.endswith(".exe"):
            subprocess.Popen([str(path), "/S"], shell=False)
        elif current_platform == "darwin" and name.endswith(".dmg"):
            subprocess.Popen(["open", str(path)], shell=False)
        else:
            # Linux AppImage or unknown — make executable and launch
            path.chmod(path.stat().st_mode | 0o111)
            subprocess.Popen([str(path)], shell=False)

    def clear_cache(self) -> None:
        """Clear the update check cache (force re-check)."""
        self._latest_result = None
        if self._cache_file.exists():
            self._cache_file.unlink(missing_ok=True)

    @property
    def cache_age_hours(self) -> float:
        """How old the cached check result is, in hours."""
        if not self._cache_file.exists():
            return float("inf")
        age = time.time() - self._cache_file.stat().st_mtime
        return age / 3600

    # ── Internal: Network ──

    def _fetch_release(self) -> UpdateCheckResult:
        """Fetch the latest release from GitHub API."""
        try:
            resp = requests.get(
                RELEASES_API,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": f"FilePilotAI/{__version__}",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.warning("Update check failed: %s", e)
            return UpdateCheckResult(
                has_update=False,
                current_version=__version__,
                error=str(e),
            )

        # Parse version from tag (e.g., "v0.3.0" -> "0.3.0")
        tag = data.get("tag_name", "")
        latest_ver = tag.lstrip("v").lstrip("V") if tag else ""

        download_url, download_size = self._select_download_asset(data.get("assets", []))

        release = ReleaseInfo(
            version=latest_ver,
            title=data.get("name", tag),
            body=data.get("body", ""),
            published_at=data.get("published_at", ""),
            html_url=data.get("html_url", ""),
            download_url=download_url,
            download_size=download_size,
        )

        has_update = self._compare_versions(latest_ver, __version__) > 0

        return UpdateCheckResult(
            has_update=has_update,
            current_version=__version__,
            release=release if has_update else None,
        )

    # ── Internal: Version comparison ──

    @staticmethod
    def _select_download_asset(assets: list[dict]) -> tuple[str | None, int]:
        """Pick the most relevant release asset for the current platform."""
        candidates: list[tuple[str, int, str | None]] = []
        for asset in assets:
            name = str(asset.get("name", ""))
            url = asset.get("browser_download_url")
            size = int(asset.get("size", 0) or 0)
            candidates.append((name, size, url))

        patterns = UpdateChecker._asset_patterns_for_platform()
        for pattern in patterns:
            for name, size, url in candidates:
                if pattern(name) and url:
                    return url, size
        return None, 0

    @staticmethod
    def _asset_patterns_for_platform() -> list[Callable[[str], bool]]:
        """Return preferred release-asset matchers for this OS."""
        current_platform = str(sys.platform)
        if current_platform.startswith("win"):
            return [
                lambda name: name.startswith("FilePilot-AI-Setup-") and name.endswith(".exe"),
                lambda name: name.endswith(".exe"),
            ]

        if current_platform == "darwin":
            return [
                lambda name: name.startswith("FilePilot-") and name.endswith(".dmg"),
                lambda name: name.endswith(".dmg"),
            ]

        machine = platform.machine().lower()
        arch_tokens = [machine]
        if machine in {"amd64", "x86_64"}:
            arch_tokens.append("x86_64")
        elif machine in {"aarch64", "arm64"}:
            arch_tokens.extend(["aarch64", "arm64"])

        return [
            lambda name: (
                name.startswith("FilePilot-")
                and name.endswith(".AppImage")
                and any(token in name.lower() for token in arch_tokens)
            ),
            lambda name: name.startswith("FilePilot-") and name.endswith(".AppImage"),
            lambda name: name.endswith(".AppImage"),
        ]

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Compare two semver strings. Returns >0 if v1 > v2."""
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
            # Pad shorter list with zeros
            max_len = max(len(parts1), len(parts2))
            parts1.extend([0] * (max_len - len(parts1)))
            parts2.extend([0] * (max_len - len(parts2)))
            for a, b in zip(parts1, parts2, strict=False):
                if a != b:
                    return a - b
            return 0
        except (ValueError, AttributeError):
            return 0

    # ── Internal: Cache ──

    def _load_cache(self) -> UpdateCheckResult | None:
        """Load cached check result if not expired."""
        try:
            if not self._cache_file.exists():
                return None
            age_hours = self.cache_age_hours
            if age_hours > CACHE_EXPIRY_HOURS:
                return None

            data = json.loads(self._cache_file.read_text(encoding="utf-8"))
            if not data:
                return None

            release_data = data.get("release")
            release = ReleaseInfo(**release_data) if release_data else None

            return UpdateCheckResult(
                has_update=data["has_update"],
                current_version=data["current_version"],
                release=release,
                error=data.get("error"),
                checked_at=data.get("checked_at", 0),
            )
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.debug("Failed to load update cache: %s", e)
            return None

    def _save_cache(self, result: UpdateCheckResult) -> None:
        """Cache the check result to disk."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "has_update": result.has_update,
                "current_version": result.current_version,
                "release": {
                    "version": result.release.version,
                    "title": result.release.title,
                    "body": result.release.body,
                    "published_at": result.release.published_at,
                    "html_url": result.release.html_url,
                    "download_url": result.release.download_url,
                    "download_size": result.release.download_size,
                }
                if result.release
                else None,
                "error": result.error,
                "checked_at": result.checked_at,
            }
            self._cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as e:
            logger.debug("Failed to save update cache: %s", e)

    def _check_thread(self, callback: Callable[[UpdateCheckResult], None] | None) -> None:
        """Background thread target."""
        result = self.check()
        if callback:
            try:
                callback(result)
            except Exception as e:
                logger.error("Update check callback failed: %s", e)


# ── Simple check (for CLI usage) ──


def check_now() -> UpdateCheckResult:
    """Convenience: run a single update check."""
    return UpdateChecker().check()


if __name__ == "__main__":
    result = check_now()
    print(f"Current version: {result.current_version}")  # noqa: T201
    if result.error:
        print(f"Error: {result.error}")  # noqa: T201
    elif result.has_update and result.release:
        print(f"Update available: {result.release.version}")  # noqa: T201
        print(f"  {result.release.html_url}")  # noqa: T201
        if result.release.download_url:
            print(f"  Download: {result.release.download_url}")  # noqa: T201
    else:
        print("You're up to date!")  # noqa: T201
