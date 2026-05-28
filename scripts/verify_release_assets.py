"""Verify release binaries and their SHA256 sidecar files.

This script is intentionally small and dependency-free so it can run in CI on
Windows, Linux, and macOS after packaging jobs produce release artifacts.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import subprocess
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_sha256_sidecar(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    expected = text.split()[0].lower() if text else ""
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError(f"{path} does not contain a valid SHA256 digest")
    return expected


def verify_checksum(artifact: Path) -> None:
    sidecar = Path(f"{artifact}.sha256")
    if not sidecar.exists():
        raise FileNotFoundError(f"Missing checksum sidecar: {sidecar}")

    expected = parse_sha256_sidecar(sidecar)
    actual = sha256_file(artifact)
    if actual != expected:
        raise ValueError(f"SHA256 mismatch for {artifact}: expected {expected}, got {actual}")


def windows_signature_status(artifact: Path) -> str | None:
    if sys.platform != "win32" or artifact.suffix.lower() != ".exe":
        return None

    escaped_artifact = str(artifact).replace("'", "''")
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$sig = Get-AuthenticodeSignature -LiteralPath "
            f"'{escaped_artifact}'; "
            "Write-Output $sig.Status"
        ),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return "Unknown"
    return result.stdout.strip() or "Unknown"


def expand_patterns(patterns: list[str]) -> list[Path]:
    artifacts: list[Path] = []
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            artifacts.extend(Path(match) for match in matches)
        else:
            candidate = Path(pattern)
            if candidate.exists():
                artifacts.append(candidate)
    return sorted({path.resolve() for path in artifacts if not path.name.endswith(".sha256")})


def verify_artifacts(
    artifacts: list[Path],
    require_windows_signature: bool = False,
    warn_windows_signature: bool = False,
) -> list[str]:
    messages: list[str] = []
    for artifact in artifacts:
        verify_checksum(artifact)
        messages.append(f"OK checksum: {artifact}")

        status = windows_signature_status(artifact)
        if status is not None:
            if status != "Valid" and require_windows_signature:
                raise ValueError(f"Invalid Windows signature for {artifact}: {status}")
            if status != "Valid" and warn_windows_signature:
                messages.append(f"WARN signature: {artifact} status={status}")
            elif status == "Valid":
                messages.append(f"OK signature: {artifact}")
    return messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify release assets against their .sha256 sidecars."
    )
    parser.add_argument("artifacts", nargs="+", help="Artifact paths or glob patterns")
    parser.add_argument(
        "--require-windows-signature",
        action="store_true",
        help="Fail if a Windows .exe does not have a valid Authenticode signature.",
    )
    parser.add_argument(
        "--warn-windows-signature",
        action="store_true",
        help="Print a warning for unsigned Windows .exe artifacts.",
    )
    args = parser.parse_args(argv)

    artifacts = expand_patterns(args.artifacts)
    if not artifacts:
        print("No release assets matched.", file=sys.stderr)
        return 1

    try:
        for message in verify_artifacts(
            artifacts,
            require_windows_signature=args.require_windows_signature,
            warn_windows_signature=args.warn_windows_signature,
        ):
            print(message)
    except Exception as e:
        print(f"Release asset verification failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
