# Release Process

> FilePilot AI — Cross-platform release checklist for maintainers.

## v0.4.0 Release Notes

**Release date:** 2026-05-14

### Key Highlights

- **Cross-platform CI** — GitHub Actions now builds on all 3 platforms: Windows (`exe` + Inno Setup), Linux (`.AppImage`), macOS (`.dmg`)
- **Cross-platform builders** — `scripts/build.sh` auto-detects OS and dispatches to the right builder (new: `build_appimage.sh` for Linux, `build_macos.sh` for macOS)
- **CI quality gates** — `mypy` + `pip check` run in all three build jobs before PyInstaller build
- **Auto-tracking Inno Setup URL** — CI fetches latest Inno Setup version dynamically
- **PEP 621 entry points** — `[project.scripts]` (`filepilot`) and `[project.gui-scripts]` (`filepilot-gui`) registered
- **macOS .icns icon** — Auto-generated from `app.png` during macOS builds
- **Architecture diagram** — `send2trash` → Recycle Bin path documented in README Mermaid flowchart

> Full changelog: [CHANGELOG.md](./CHANGELOG.md)

---

## Overview

Each release produces three platform-specific artifacts via GitHub Actions CI:

| Platform | Artifact | Builder |
|----------|----------|---------|
| Windows  | `FilePilot-AI-Setup-<version>.exe` | `scripts/build_installer.ps1` + Inno Setup |
| Linux    | `FilePilot-<version>-<arch>.AppImage` | `scripts/build_appimage.sh` |
| macOS    | `FilePilot-<version>.dmg` | `scripts/build_macos.sh` |

---

## 1. Pre-Release Checklist

Run these **before** tagging. CI will also enforce them, but catching issues early saves a push cycle.

```bash
# ── Full test suite ──
pytest tests/ -q

# ── Static analysis ──
ruff check .

# ── Type checking ──
mypy

# ── Syntax check on all Python files ──
python check_syntax.py

# ── Build script syntax (bash) ──
bash -n scripts/build.sh
bash -n scripts/build_appimage.sh
bash -n scripts/build_macos.sh

# ── Build script syntax (PowerShell) ──
# Run on Windows only:
powershell -NoProfile -Command "& { . .\scripts\build_installer.ps1; Write-Host 'Syntax OK' }"

# ── Inno Setup script validation (Windows only) ──
# Requires ISCC in PATH:
iscc scripts\filepilot-installer.iss
```

### Manual verification

- [ ] **Version consistency** — Check all files report the same version:
  - `filepilot/__init__.py` — `__version__`
  - `pyproject.toml` — `project.version`
  - `CHANGELOG.md` — version header and release date
  - `README.md` — any version references in badges or text
  - Fallback versions in build scripts (`build_installer.ps1`, `build_appimage.sh`, `build_macos.sh`) — they default to `0.0.0` or auto-detect, so no manual update needed.
- [ ] **CHANGELOG.md** — Entry for the new version is complete and accurate. Follow the existing format:
  ```markdown
  ## [0.4.0] - 2026-05-14

  ### Added
  - **Feature** — description

  ### Fixed
  - **Bug** — description

  ### Changed
  - **Change** — description
  ```
- [ ] **Git status is clean** — `git status` shows no uncommitted changes.
- [ ] **Tests pass on all three platforms** (CI will confirm this, but run locally for your primary platform).

---

## 2. Tagging

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create a signed tag
git tag -a v0.4.0 -m "v0.4.0"

# Push the tag (triggers CI build)
git push origin v0.4.0
```

> **Tag format:** `v<major>.<minor>.<patch>` — always lowercase `v`, no spaces.
>
> Pushing a tag triggers the **Release** workflow in `.github/workflows/ci.yml`, which:
> 1. Runs `build-windows` job (PyInstaller → Inno Setup → sign if available → SHA256)
> 2. Runs `build-linux` job (PyInstaller → AppImage)
> 3. Runs `build-macos` job (PyInstaller → .app → codesign → notarize → DMG)
> 4. Uploads all artifacts to the workflow run

### CI workflow reference

| Job | Runner | Output artifact |
|-----|--------|----------------|
| `build-windows` | `windows-latest` | `FilePilot-AI-Setup-<version>.exe` + `.sha256` |
| `build-linux` | `ubuntu-latest` | `FilePilot-<version>-<arch>.AppImage` |
| `build-macos` | `macos-latest` | `FilePilot-<version>.dmg` |

---

## 3. Artifact Verification

After CI completes (check **Actions** tab in GitHub), download the artifacts and verify:

```bash
# Check SHA256
sha256sum FilePilot-AI-Setup-*.exe

# Verify the .exe is a valid Inno Setup installer (Windows)
file FilePilot-AI-Setup-*.exe
# Expected: "PE32+ executable (GUI) ... Inno Setup"

# Verify the .AppImage is executable (Linux)
chmod +x FilePilot-*.AppImage
./FilePilot-*.AppImage --appimage-extract  # dry-run to verify structure

# Verify the .dmg mounts correctly (macOS)
hdiutil attach FilePilot-*.dmg
ls /Volumes/FilePilot\ AI/
# Expected: FilePilot.app + Applications symlink
hdiutil detach /Volumes/FilePilot\ AI/
```

### Quick smoke test (optional but recommended)

Run the installer on each platform and confirm:
- [ ] Application launches without crash
- [ ] Version displayed in About dialog matches the release
- [ ] Basic search / index / organize functions work
- [ ] Auto-update check (`python -m filepilot.updater`) reports "You're up to date!"

---

## 4. GitHub Release

1. Go to **https://github.com/cuiheng511/filepilot-ai/releases/new**
2. Choose the tag you just pushed (e.g., `v0.4.0`)
3. **Release title:** `v0.4.0`
4. **Description:** Paste the CHANGELOG entry for this version.
   - Include installation instructions:
     ```markdown
     ## Downloads

     | Platform | File |
     |----------|------|
     | Windows  | `FilePilot-AI-Setup-0.4.0.exe` |
     | Linux    | `FilePilot-0.4.0-x86_64.AppImage` |
     | macOS    | `FilePilot-0.4.0.dmg` |

     ## Installation

     ### Windows
     Run the `.exe` installer. Admin rights required by default (override with `ALLUSERS=1`).

     ### Linux
     ```bash
     chmod +x FilePilot-0.4.0-x86_64.AppImage
     ./FilePilot-0.4.0-x86_64.AppImage
     ```

     ### macOS
     Open the `.dmg` and drag `FilePilot.app` to your `Applications` folder.
     ```
   - Attach the `## Changelog` section from CHANGELOG.md
5. **Attach binaries:** Drag all CI artifacts into the attachment area:
   - `FilePilot-AI-Setup-<version>.exe`
   - `FilePilot-AI-Setup-<version>.exe.sha256`
   - `FilePilot-<version>-<arch>.AppImage`
   - `FilePilot-<version>.dmg`
6. ⚠️ **Mark as "Set as the latest release"** (default)
7. Click **Publish release**

---

## 5. Post-Release

- [ ] **Verify auto-update** — On a separate machine, run the old version and check that it detects the new release:
  ```bash
  python -m filepilot.updater
  # Expected: "Update available: 0.4.0"
  ```
- [ ] **Close the milestone** — If you use GitHub Milestones, close the corresponding milestone.
- [ ] **Update `CHANGELOG.md`** — Add a new `## [Unreleased]` section at the top for the next cycle:
  ```markdown
  ## [Unreleased]

  ### Added

  ### Fixed

  ### Changed
  ```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| CI job fails on `build-windows` — "ISCC.exe not found" | CI couldn't download Inno Setup | Check the Inno Setup download URL in `.github/workflows/ci.yml` still works |
| CI job fails on `build-linux` — "appimagetool: command not found" | GitHub runner updated and removed FUSE support | Set `APPIMAGE_EXTRACT_AND_RUN=1` (already done in the script) |
| macOS DMG contains folder contents instead of .app | `create-dmg` source path issue | Verify `$DMG_DIR` contains the `.app` bundle, not its contents |
| Version shows wrong number in installer | Version not passed correctly | Check `build_installer.ps1` line 166 and CI step that passes `/dMyAppVersion=` |
| `iscc` fails with "Couldn't open include file ChineseSimplified.isl" | ChineseSimplified.isl not bundled with default Inno Setup winget/choco install | Download from [jrsoftware.org](https://jrsoftware.org/download.php/ChineseSimplified.isl) to Inno Setup `Languages\` dir, or comment out `chinesesimplified` in `.iss` |
| Release not appearing in updater | GitHub Releases API rate limit or tag mismatch | Check `filepilot/updater.py` repository URL and tag format |
