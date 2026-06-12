# Building FilePilot AI

> Cross-platform packaging guide for Windows, Linux, and macOS.

---

## Overview

FilePilot AI is packaged using **PyInstaller** on all three platforms, with platform-specific wrappers:

| Platform | Package Type | Script | Artifact |
|----------|-------------|--------|----------|
| Windows | Installer (Inno Setup) | `scripts/build_installer.ps1` | `.exe` installer |
| Linux | AppImage | `scripts/build_appimage.sh` | `.AppImage` |
| macOS | .app + .dmg | `scripts/build_macos.sh` | `.dmg` |

The unified entry point `scripts/build.sh` auto-detects your OS and dispatches to the appropriate script.

---

## Prerequisites

### All Platforms

- Python 3.10 or newer
- PyInstaller (`pip install pyinstaller`)
- Project dependencies: `pip install -r requirements.txt`

### Windows

- **Inno Setup 6** — [Download](https://github.com/jrsoftware/issrc/releases) (use GitHub Releases — `jrsoftware.org/isdl.php` returns 404 as of 2026)
  - Ensure `ISCC.exe` is in your PATH, or set `ISCC_DIR` environment variable
- Optional: **Authenticode certificate** for code signing

### Linux

- **appimagetool** — downloaded automatically by the build script if missing
- `FUSE` — required to run AppImage (may not be needed for build)
- Docker (optional) — for building Linux AppImage from a non-Linux host via `--docker-linux`

### macOS

- macOS 12+ (Monterey or newer)
- Xcode Command Line Tools: `xcode-select --install`
- **create-dmg** — [Download](https://github.com/create-dmg/create-dmg) or `brew install create-dmg`
- Apple Developer ID (optional) — for code signing and notarization

---

## Quick Build

```bash
# Auto-detect platform and build
./scripts/build.sh

# Build for a specific platform
./scripts/build_appimage.sh              # Linux AppImage
./scripts/build_macos.sh --sign          # macOS .app + .dmg (signed)
./scripts/build.sh --docker-linux        # Linux AppImage via Docker (any OS)
.\scripts\build_installer.ps1            # Windows installer (Inno Setup)
```

Build artifacts are written to the `dist/` directory.

---

## Windows Installer

### How It Works

1. **PyInstaller** compiles `filepilot/` into `dist/FilePilot/FilePilot.exe`
2. **Inno Setup** (`ISCC.exe`) compiles `scripts/filepilot-installer.iss` into a setup executable
3. **SHA256 checksum** is generated alongside the installer

### Inno Setup Configuration

The installer configuration lives at `scripts/filepilot-installer.iss` and handles:

- **Installation path**: `%LOCALAPPDATA%\Programs\FilePilot AI`
- **Shortcuts**: Start Menu and Desktop
- **File association**: `.fpindex` files
- **Registry**: Installation path and version stored in `HKCU`
- **Pre-install check**: Automatically closes a running `FilePilot.exe` before installation

### Code Signing (Optional)

Set these environment variables before running the build:

```powershell
$env:SIGNTOOL_PATH = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe"
$env:SIGN_CERTIFICATE_SHA1 = "YOUR_CERTIFICATE_SHA1_HASH"
```

When set, the build script will sign `FilePilot.exe`, `unins000.exe`, and the setup executable.

### Localized Installer

By default the installer is English-only. To add Chinese Simplified:

1. Download `ChineseSimplified.isl` from [jrsoftware.org](https://jrsoftware.org/isdl.php)
2. Place it in Inno Setup's `Languages` directory (e.g. `C:\Program Files (x86)\Inno Setup 6\Languages\`)
3. In `scripts/filepilot-installer.iss`, add the following line after the existing `english` entry:

```iss
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
```

---

## Linux AppImage

### Build Process

1. **PyInstaller** builds into `dist/FilePilot/` using a custom spec file with explicit hidden imports
2. **AppDir** is prepared with:
   - `usr/bin/` — application binary
   - `usr/share/applications/` — `.desktop` file
   - `usr/share/icons/` — application icons (all standard sizes)
   - `usr/share/metainfo/` — AppStream metadata
   - `AppRun` — entry-point script
3. **appimagetool** packages the AppDir into a portable `.AppImage`

The script downloads `appimagetool` automatically if not found.

### Docker Build

To build a Linux AppImage from Windows or macOS:

```bash
./scripts/build.sh --docker-linux
```

This uses a Docker container to run the Linux build pipeline regardless of the host OS.

### Output

```
dist/FilePilot-{version}-x86_64.AppImage
```

The AppImage is portable — no installation required, runs on any Linux distribution.

---

## macOS .app + .dmg

### Build Process

1. **Icon generation**: `app.icns` is auto-generated from `filepilot/resources/app.png` using `sips` and `iconutil`
2. **PyInstaller** builds a macOS `.app` bundle (`--onedir`, `--windowed`)
3. **Code signing** (optional): Signs the `.app` bundle with `codesign`
4. **Notarization** (optional): Submits to Apple Notary Service
5. **DMG creation**: Packages the `.app` into a `.dmg` using `create-dmg` (primary) or `hdiutil` (fallback)

### Code Signing & Notarization

```bash
# Sign only
./scripts/build_macos.sh --sign

# Sign and notarize
./scripts/build_macos.sh --sign --notarize
```

Requires:
- Apple Developer ID certificate in your keychain
- `APPLE_ID` and `APPLE_ID_PASSWORD` environment variables for notarization
- Valid `--bundle-identifier` in the build script

### Output

```
dist/FilePilot.app
dist/FilePilot-{version}.dmg
```

---

## CI Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) builds all three platforms automatically on every push to `main` and on `v*` release tags:

| Job | Platform | Runner | Artifact | Retention |
|-----|----------|--------|----------|-----------|
| `build-windows` | Windows | `windows-latest` | `.exe` installer | 30 days |
| `build-linux` | Linux | `ubuntu-latest` | `.AppImage` | 30 days |
| `build-macos` | macOS | `macos-latest` | `.dmg` | 30 days |

Each CI run:
1. Runs lint and test stages first
2. Executes quality gates (`pip check`, `mypy`) before building
3. Produces SHA256 checksums alongside the artifacts
4. Uploads artifacts to the GitHub Actions run summary
5. Publishes a GitHub Release automatically when the run was triggered by a `v*` tag

---

## Troubleshooting

### PyInstaller "hidden import" errors

If the built application crashes with missing module errors, add hidden imports to the build script or spec file:

| Platform | Where to add hidden imports |
|----------|---------------------------|
| Windows | `FilePilot.spec` — `hiddenimports` list in the `Analysis` section |
| Linux | `scripts/build_appimage.sh` — the inline spec generated in the `cat > FilePilot-linux.spec << 'EOF'` block |
| macOS | `scripts/build_macos.sh` — the `--hidden-import` flags in the PyInstaller command |

> **Important**: hidden imports must be kept in sync across **4 files**: `FilePilot.spec`, `scripts/build_appimage.sh` (inline spec), `scripts/build_macos.sh` (CLI flags), and `.github/workflows/ci.yml` (Linux + macOS CLI flags in the `build-linux` and `build-macos` jobs). Missing imports cause runtime crashes after packaging.

Common hidden imports used across platforms:

```
PySide6.QtCore
PySide6.QtWidgets
PySide6.QtGui
filepilot.ai
filepilot.core
filepilot.extractors
filepilot.ui
filepilot.utils
whoosh
send2trash
PIL
markdown
docx
openpyxl
pptx
```

### Inno Setup not found

```powershell
# Set the path explicitly
$env:ISCC_DIR = "C:\Program Files (x86)\Inno Setup 6"
.\scripts\build_installer.ps1
```

### macOS code signing fails

- Ensure the certificate is in your login keychain
- Run `security find-identity -v -p basic` to list available signing identities
- Pass `--bundle-identifier` explicitly if the default doesn't match your provisioning profile

### AppImage fails on older Linux distributions

Build with Docker to use a consistent base system:

```bash
./scripts/build.sh --docker-linux
```
