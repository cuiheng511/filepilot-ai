"""Config — Unified settings persistence with JSON + encrypted API key storage.

API keys are stored encrypted using one of two mechanisms (tried in order):
1. System keyring (keyring package) — OS-native encrypted credential store
2. Fernet-encrypted file (cryptography package) — fallback when keyring unavailable

Encrypted key file lives at ~/.filepilot/api_key.enc
The encryption key is derived from a machine-local salt file ~/.filepilot/.key_salt
"""

import base64
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("filepilot.config")

SETTINGS_DIR = Path.home() / ".filepilot"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
ENCRYPTED_KEY_FILE = SETTINGS_DIR / "api_key.enc"
SALT_FILE = SETTINGS_DIR / ".key_salt"
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


# ── Machine-local encryption key derivation ───────────────────────────────


def _ensure_salt() -> bytes:
    """Read or generate a persistent salt file for key derivation."""
    if SALT_FILE.exists():
        raw = SALT_FILE.read_bytes()
        if len(raw) >= 16:
            return raw[:16]
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    salt = os.urandom(16)
    SALT_FILE.write_bytes(salt)
    return salt


def _get_fernet_key() -> bytes | None:
    """Derive a Fernet-compatible 32-byte key from machine-local data + salt.

    Returns None if cryptography is not installed.
    """
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError:
        return None

    try:
        salt = _ensure_salt()
        # Use machine hostname + a fixed local identifier as the "password"
        material = (
            os.uname().nodename.encode("utf-8") if hasattr(os, "uname") else b"filepilot-local"
        )
        # On Windows, use COMPUTERNAME instead
        if not material or material == b"filepilot-local":
            material = os.environ.get("COMPUTERNAME", "filepilot-local").encode("utf-8")

        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
        key = base64.urlsafe_b64encode(kdf.derive(material))
        return key
    except Exception:
        return None


def _encrypt_api_key(api_key: str) -> bytes | None:
    """Encrypt API key with Fernet. Returns None on failure."""
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None
    key = _get_fernet_key()
    if key is None:
        return None
    try:
        f = Fernet(key)
        return bytes(f.encrypt(api_key.encode("utf-8")))
    except Exception:
        return None


def _decrypt_api_key(token: bytes) -> str | None:
    """Decrypt Fernet-encrypted API key. Returns None on failure."""
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None
    key = _get_fernet_key()
    if key is None:
        return None
    try:
        f = Fernet(key)
        return str(f.decrypt(token).decode("utf-8"))
    except Exception:
        return None


# ── Keyring (OS-level encrypted storage) ──────────────────────────────────


def _get_keyring_key() -> str:
    """Read API key from OS keyring or encrypted fallback file."""
    # Try system keyring first
    try:
        import keyring

        key = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
        if key:
            return str(key)
    except Exception:
        pass
    # Fallback: try encrypted file
    if ENCRYPTED_KEY_FILE.exists():
        try:
            token = ENCRYPTED_KEY_FILE.read_bytes()
            decrypted = _decrypt_api_key(token)
            if decrypted:
                return decrypted
        except Exception:
            pass
    return ""


def _save_keyring_key(api_key: str) -> bool:
    """Save API key to OS keyring. Falls back to encrypted file if keyring unavailable."""
    if not api_key:
        return True
    saved_to = []
    # Try system keyring
    try:
        import keyring

        keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, api_key)
        saved_to.append("keyring")
    except Exception:
        pass
    # Always update encrypted file as a fallback
    encrypted = _encrypt_api_key(api_key)
    if encrypted is not None:
        try:
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            ENCRYPTED_KEY_FILE.write_bytes(encrypted)
            saved_to.append("file")
        except Exception:
            pass
    return len(saved_to) > 0


def load() -> dict:
    settings = dict(DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            user = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            keyring_key = _get_keyring_key()
            if keyring_key:
                user["ai_api_key"] = keyring_key
            elif user.get("ai_api_key"):
                _save_keyring_key(user["ai_api_key"])
            settings.update(user)
        except Exception as e:
            logger.warning("Failed to load settings: %s", e)
    return settings


def save(settings: dict):
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    settings_copy = dict(settings)
    api_key = settings_copy.pop("ai_api_key", "")
    if api_key:
        _save_keyring_key(api_key)
    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings_copy, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("Failed to save settings: %s", e)
