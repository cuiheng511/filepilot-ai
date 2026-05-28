# Release Process

> FilePilot AI — Cross-platform release checklist for maintainers.

## Current Release: v0.6.4

**Release date:** 2026-05-28

See [CHANGELOG.md](./CHANGELOG.md) for the full history.

### Quick Links

| Platform | Download |
|----------|----------|
| Windows  | `FilePilot-AI-Setup-0.6.4.exe` |
| Linux    | `FilePilot-0.6.4-x86_64.AppImage` |
| macOS    | `FilePilot-0.6.4.dmg` |

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
  - Fallback versions in build scripts (`build_installer.ps1`, `build_appimage.sh`, `build_macos.sh`) match the current release or auto-detect from `filepilot/__init__.py`.
- [ ] **CHANGELOG.md** — Entry for the new version is complete and accurate. Follow the existing format:
  ```markdown
  ## [X.Y.Z] - YYYY-MM-DD

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

# Create a signed tag (replace X.Y.Z with actual version)
git tag -a vX.Y.Z -m "vX.Y.Z"

# Push the tag (triggers CI build)
git push origin vX.Y.Z
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

# Or verify all packaged assets against their sidecars
python scripts/verify_release_assets.py \
  "dist/FilePilot-AI-Setup-*.exe" \
  "dist/FilePilot-*.AppImage" \
  "dist/FilePilot-*.dmg"

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

### Signing and notarization

- Windows signing is enabled by `SIGNTOOL_PATH` and `SIGN_CERTIFICATE_SHA1` in `scripts/build_installer.ps1`.
- macOS signing and notarization are enabled by `scripts/build_macos.sh --sign --notarize` and the Apple Developer environment variables documented in that script.
- CI always verifies `.sha256` sidecars. For a stricter local Windows release check, run `python scripts/verify_release_assets.py "dist/FilePilot-AI-Setup-*.exe" --require-windows-signature` after signing.

---

## 4. GitHub Release

1. Go to **https://github.com/cuiheng511/filepilot-ai/releases/new**
2. Choose the tag you just pushed (e.g., `v0.6.4`)
3. **Release title:** `v0.6.4`
4. **Description:** Paste the CHANGELOG entry for this version.
   - Include installation instructions (replace `X.Y.Z` with the actual version):
     ```markdown
     ## Downloads

     | Platform | File |
     |----------|------|
     | Windows  | `FilePilot-AI-Setup-X.Y.Z.exe` |
     | Linux    | `FilePilot-X.Y.Z-x86_64.AppImage` |
     | macOS    | `FilePilot-X.Y.Z.dmg` |

     ## Installation

     ### Windows
     Run the `.exe` installer.

     ### Linux
     ```bash
     chmod +x FilePilot-X.Y.Z-x86_64.AppImage
     ./FilePilot-X.Y.Z-x86_64.AppImage
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
  # Expected: "Update available: X.Y.Z"
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
