"""Cloud Sync Detection — identify files in cloud-synced folders.

Detects OneDrive, Dropbox, Google Drive, and iCloud Drive sync folders.
Provides status indicators for files within these directories.
"""

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("filepilot.cloud_sync")


@dataclass
class CloudProvider:
    """Represents a detected cloud sync provider."""

    name: str
    icon: str
    root_path: Path
    status: str = "synced"  # synced, syncing, offline, unknown


# Known cloud provider detection paths
_PROVIDER_PATHS: dict[str, list[str]] = {
    "OneDrive": [
        os.environ.get("ONEDRIVE", ""),
        os.environ.get("ONEDRIVECONSUMER", ""),
        os.environ.get("ONEDRIVECOMMERCIAL", ""),
        str(Path.home() / "OneDrive"),
        str(Path.home() / "OneDrive - Personal"),
    ],
    "Dropbox": [
        str(Path.home() / "Dropbox"),
        str(Path.home() / "Dropbox (Personal)"),
    ],
    "Google Drive": [
        str(Path.home() / "Google Drive"),
        str(Path.home() / "My Drive"),
    ],
    "iCloud Drive": [
        str(Path.home() / "iCloudDrive"),
    ],
}

# Add platform-specific paths
if sys.platform == "win32":
    _PROVIDER_PATHS["Google Drive"].append(
        str(Path(os.environ.get("USERPROFILE", "")) / "Google Drive")
    )
    _PROVIDER_PATHS["iCloud Drive"].append(
        str(Path(os.environ.get("USERPROFILE", "")) / "iCloudDrive")
    )
elif sys.platform == "darwin":
    _PROVIDER_PATHS["iCloud Drive"].append(
        str(Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs")
    )
    _PROVIDER_PATHS["Google Drive"].append(str(Path.home() / "Library" / "CloudStorage"))

_PROVIDER_ICONS = {
    "OneDrive": "☁️",
    "Dropbox": "📦",
    "Google Drive": "🔺",
    "iCloud Drive": "🍎",
}


def detect_cloud_providers() -> list[CloudProvider]:
    """Detect all active cloud sync providers on this machine.

    Returns:
        List of detected CloudProvider instances with valid root paths.
    """
    providers = []
    seen_paths: set[str] = set()

    for name, paths in _PROVIDER_PATHS.items():
        for path_str in paths:
            if not path_str:
                continue
            path = Path(path_str)
            if path.exists() and path.is_dir() and str(path) not in seen_paths:
                providers.append(
                    CloudProvider(
                        name=name,
                        icon=_PROVIDER_ICONS.get(name, "☁️"),
                        root_path=path,
                        status="synced",
                    )
                )
                seen_paths.add(str(path))
                break  # Only first valid path per provider

    return providers


def get_cloud_status(file_path: str | Path) -> CloudProvider | None:
    """Check if a file is within a cloud-synced folder.

    Args:
        file_path: Path to check.

    Returns:
        CloudProvider if the file is in a sync folder, None otherwise.
    """
    path = Path(file_path).resolve()
    providers = detect_cloud_providers()

    for provider in providers:
        try:
            if path.is_relative_to(provider.root_path):
                return provider
        except (ValueError, TypeError):
            continue

    return None


def get_cloud_status_batch(file_paths: list[str | Path]) -> dict[str, CloudProvider | None]:
    """Check cloud status for multiple files efficiently.

    Caches provider detection to avoid repeated filesystem checks.

    Args:
        file_paths: List of paths to check.

    Returns:
        Dict mapping path string -> CloudProvider or None.
    """
    providers = detect_cloud_providers()
    results: dict[str, CloudProvider | None] = {}

    for fp in file_paths:
        path = Path(fp).resolve()
        matched = None
        for provider in providers:
            try:
                if path.is_relative_to(provider.root_path):
                    matched = provider
                    break
            except (ValueError, TypeError):
                continue
        results[str(fp)] = matched

    return results


def get_onedrive_file_status(file_path: str | Path) -> str:
    """Get OneDrive-specific file status on Windows.

    Uses file attributes to determine if a file is:
    - 'cloud_only': Available online only (placeholder)
    - 'synced': Fully downloaded and synced
    - 'syncing': Currently syncing
    - 'unknown': Cannot determine

    Only works on Windows with OneDrive. Returns 'unknown' on other platforms.
    """
    if sys.platform != "win32":
        return "unknown"

    try:  # type: ignore[unreachable]
        import ctypes

        path = str(Path(file_path).resolve())
        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
        if attrs == -1:
            return "unknown"

        # FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
        # FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
        # FILE_ATTRIBUTE_PINNED = 0x00080000
        # FILE_ATTRIBUTE_UNPINNED = 0x00100000
        recall_on_data = 0x00400000
        recall_on_open = 0x00040000

        if attrs & recall_on_data or attrs & recall_on_open:
            return "cloud_only"
        return "synced"
    except Exception:
        return "unknown"
