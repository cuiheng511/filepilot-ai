"""Tests for release asset checksum verification."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_release_assets.py"
SPEC = importlib.util.spec_from_file_location("verify_release_assets", SCRIPT_PATH)
assert SPEC
assert SPEC.loader
verify_release_assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_release_assets)


def test_verify_artifacts_accepts_matching_sha256(tmp_path):
    artifact = tmp_path / "FilePilot.AppImage"
    content = b"release-binary"
    artifact.write_bytes(content)
    artifact.with_name(f"{artifact.name}.sha256").write_text(
        f"{hashlib.sha256(content).hexdigest()}  {artifact.name}\n",
        encoding="utf-8",
    )

    messages = verify_release_assets.verify_artifacts([artifact])

    assert messages == [f"OK checksum: {artifact}"]


def test_verify_artifacts_rejects_mismatched_sha256(tmp_path):
    artifact = tmp_path / "FilePilot.dmg"
    artifact.write_bytes(b"release-binary")
    artifact.with_name(f"{artifact.name}.sha256").write_text("0" * 64, encoding="utf-8")

    with pytest.raises(ValueError, match="SHA256 mismatch"):
        verify_release_assets.verify_artifacts([artifact])


def test_expand_patterns_handles_globs(tmp_path):
    artifact = tmp_path / "FilePilot.exe"
    artifact.write_bytes(b"x")
    artifact.with_name(f"{artifact.name}.sha256").write_text("0" * 64, encoding="utf-8")

    matches = verify_release_assets.expand_patterns([str(tmp_path / "FilePilot*")])

    assert matches == [artifact.resolve()]
