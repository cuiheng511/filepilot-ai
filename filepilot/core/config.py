"""Config — Unified settings persistence with JSON + system keyring support"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("filepilot.config")

SETTINGS_DIR = Path.home() / ".filepilot"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
KEYRING_SERVICE = "filepilot-ai"
KEYRING_KEY = "ai_api_key"

DEFAULTS = {
    "ai_mode": "local",
    "ai_provider": "ollama",
    "ai_model": "qwen2.5:7b",
    "ai_api_base": "http://localhost:11434",
    "ai_api_key": "",
    "index_dir": "~/.filepilot/index",
    "max_file_size_mb": 500,
    "theme": "dark",
    "language": "en",
    "recent_dirs": [],
}


def _get_keyring_key() -> str:
    try:
        import keyring
        key = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
        return key or ""
    except Exception:
        return ""


def _save_keyring_key(api_key: str) -> bool:
    if not api_key:
        return True
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, api_key)
        return True
    except Exception:
        return False


def load() -> dict:
    settings = dict(DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            user = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            keyring_key = _get_keyring_key()
            if keyring_key:
                user["ai_api_key"] = keyring_key
            elif "ai_api_key" in user and user["ai_api_key"]:
                _save_keyring_key(user["ai_api_key"])
            settings.update(user)
        except Exception as e:
            logger.warning("Failed to load settings: %s", e)
    return settings


def save(settings: dict):
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    api_key = settings.pop("ai_api_key", "")
    if api_key:
        _save_keyring_key(api_key)
    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("Failed to save settings: %s", e)
    finally:
        settings["ai_api_key"] = api_key
