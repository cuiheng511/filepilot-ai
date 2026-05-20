"""Auto-start with OS platform-specific registration."""

import contextlib
import html
import logging
import shlex
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _winreg():
    """Lazy import of winreg (Windows-only)."""
    if sys.platform.startswith("win"):
        import winreg as _wr

        return _wr
    return None


def is_auto_start_enabled() -> bool:
    """Check if the app is registered to auto-start with the OS."""
    current = str(sys.platform)
    if current.startswith("win"):
        return _windows_is_enabled()
    if current == "darwin":
        return _macos_is_enabled()
    return _linux_is_enabled()


def set_auto_start(enabled: bool) -> None:
    """Register or unregister the app for auto-start with the OS."""
    current = str(sys.platform)
    if current.startswith("win"):
        _windows_set(enabled)
    elif current == "darwin":
        _macos_set(enabled)
    else:
        _linux_set(enabled)


def _get_executable_args() -> list[str]:
    """Return argv for launching the current app."""
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve())]
    return [str(Path(sys.executable).resolve()), "-m", "filepilot.main"]


def _get_executable() -> str:
    """Return a shell-safe command string for startup registries."""
    args = _get_executable_args()
    if str(sys.platform).startswith("win"):
        return subprocess.list2cmdline(args)
    return " ".join(shlex.quote(arg) for arg in args)


# ── Windows ──

_WIN_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_WIN_APP_NAME = "FilePilotAI"


def _windows_is_enabled() -> bool:
    try:
        wr = _winreg()
        if wr is None:
            return False
        with wr.OpenKey(wr.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, wr.KEY_READ) as key:
            value, _ = wr.QueryValueEx(key, _WIN_APP_NAME)
            return bool(value)
    except (FileNotFoundError, OSError):
        return False


def _windows_set(enabled: bool) -> None:
    try:
        wr = _winreg()
        if wr is None:
            return
        with wr.CreateKeyEx(wr.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, wr.KEY_SET_VALUE) as key:
            if enabled:
                wr.SetValueEx(key, _WIN_APP_NAME, 0, wr.REG_SZ, _get_executable())
            else:
                with contextlib.suppress(FileNotFoundError):
                    wr.DeleteValue(key, _WIN_APP_NAME)
        logger.info("Auto-start %s on Windows", "enabled" if enabled else "disabled")
    except OSError as e:
        logger.warning("Failed to set auto-start on Windows: %s", e)


# ── macOS ──

_MACOS_PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
_MACOS_PLIST = _MACOS_PLIST_DIR / "com.filepilot-ai.plist"


def _macos_is_enabled() -> bool:
    return _MACOS_PLIST.exists()


def _macos_set(enabled: bool) -> None:
    try:
        if enabled:
            _MACOS_PLIST_DIR.mkdir(parents=True, exist_ok=True)
            args_xml = "".join(
                f"        <string>{html.escape(arg)}</string>\n" for arg in _get_executable_args()
            )
            _MACOS_PLIST.write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                '<plist version="1.0">\n'
                "<dict>\n"
                "    <key>Label</key>\n"
                "    <string>com.filepilot-ai</string>\n"
                "    <key>ProgramArguments</key>\n"
                "    <array>\n"
                f"{args_xml}"
                "    </array>\n"
                "    <key>RunAtLoad</key>\n"
                "    <true/>\n"
                "</dict>\n"
                "</plist>\n",
                encoding="utf-8",
            )
        else:
            _MACOS_PLIST.unlink(missing_ok=True)
        logger.info("Auto-start %s on macOS", "enabled" if enabled else "disabled")
    except OSError as e:
        logger.warning("Failed to set auto-start on macOS: %s", e)


# ── Linux ──

_LINUX_AUTOSTART_DIR = Path.home() / ".config" / "autostart"
_LINUX_DESKTOP = _LINUX_AUTOSTART_DIR / "filepilot-ai.desktop"


def _linux_is_enabled() -> bool:
    return _LINUX_DESKTOP.exists()


def _linux_set(enabled: bool) -> None:
    try:
        if enabled:
            _LINUX_AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
            _LINUX_DESKTOP.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=FilePilot AI\n"
                f"Exec={_get_executable()}\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n",
                encoding="utf-8",
            )
        else:
            _LINUX_DESKTOP.unlink(missing_ok=True)
        logger.info("Auto-start %s on Linux", "enabled" if enabled else "disabled")
    except OSError as e:
        logger.warning("Failed to set auto-start on Linux: %s", e)
