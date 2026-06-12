# Release Process

> FilePilot AI cross-platform release checklist for maintainers.

## Current Release

Current project version: `0.8.0`

See [CHANGELOG.md](./CHANGELOG.md) for the full release history.

## What CI Builds

The main CI workflow builds and verifies release-ready desktop artifacts:

| Platform | Artifact | Builder |
| --- | --- | --- |
| Windows | `FilePilot-AI-Setup-<version>.exe` + `.sha256` | PyInstaller + Inno Setup |
| Linux | `FilePilot-<version>-<arch>.AppImage` + `.sha256` | PyInstaller + AppImage |
| macOS | `FilePilot-<version>.dmg` + `.sha256` | PyInstaller `.app` + DMG |

On normal `main` pushes, build artifacts are uploaded to the workflow run and
named with the commit SHA. On `v*` tag pushes, artifacts are named with the tag
and the workflow publishes a GitHub Release automatically.

## 1. Pre-Release Checklist

Run these before tagging. CI will also enforce them, but local checks catch
simple mistakes before a release tag is pushed.

```bash
pre-commit run --all-files
python -m pytest tests/ -q
ruff check .
ruff format --check .
mypy
python scripts/verify_release_assets.py --help
```

Manual checks:

- Confirm version consistency in `filepilot/__init__.py`, `pyproject.toml`,
  `README.md`, and `CHANGELOG.md`.
- Confirm `CHANGELOG.md` has a dated entry for the release version.
- Confirm `CHANGELOG.md` does not overstate shipped behavior.
- Confirm `git status` is clean.
- Confirm the latest `main` CI run is green.

## 2. Tagging

Create and push an annotated tag:

```bash
git checkout main
git pull origin main
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

Tag format is always `v<major>.<minor>.<patch>`, for example `v0.8.0`.

Pushing a `v*` tag triggers `.github/workflows/ci.yml`. The workflow:

1. Runs lint and tests.
2. Builds Windows, Linux, and macOS desktop artifacts.
3. Generates `.sha256` checksum sidecars.
4. Verifies packaged assets with `scripts/verify_release_assets.py`.
5. Downloads the final installer artifacts into a release job.
6. Creates a GitHub Release with notes extracted from `CHANGELOG.md`.

## 3. After CI Completes

Check the tag workflow run in GitHub Actions:

- All lint, test, MCP smoke, and build jobs are green.
- The `Publish GitHub Release` job succeeded.
- The release contains Windows installer, Linux AppImage, macOS DMG, and
  matching `.sha256` files.
- The release notes match the intended `CHANGELOG.md` entry.

If the publish job fails after artifacts were built, download the workflow
artifacts and create the release manually:

```bash
gh release create vX.Y.Z release-assets/* \
  --title "FilePilot AI vX.Y.Z" \
  --notes-file release-notes.md \
  --verify-tag
```

## 4. Optional Smoke Tests

Before announcing a release, test one fresh install path when possible:

- Windows: run the `.exe` installer and launch FilePilot AI.
- Linux: mark the AppImage executable and launch it.
- macOS: open the DMG and drag `FilePilot.app` to Applications.
- Confirm the app reports the expected version.
- Confirm scanning, search, and one read-only MCP command still work.

## 5. Post-Release

- Verify the release page is marked as latest.
- Verify the auto-update checker sees the new release.
- Close or update any release milestone.
- Add a fresh `## [Unreleased]` section if it was consumed during release prep.
- Start the next small version only after CI is green on the tag.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Tag push does not start CI | Tag does not match `v*` | Push a tag like `v0.8.0`. |
| Release job cannot find an artifact | A platform build failed or upload was skipped | Check the build job logs before retrying the release job. |
| Release notes step fails | Missing matching `CHANGELOG.md` entry | Add `## [X.Y.Z] - YYYY-MM-DD` before tagging. |
| Windows installer build fails | Inno Setup download or compile issue | Check the Inno Setup step and `scripts/filepilot-installer.iss`. |
| AppImage is missing | AppImage tool or FUSE compatibility issue | Check the Linux build log and `scripts/build_appimage.sh`. |
| DMG is missing | `.app` bundle or DMG packaging failed | Check the macOS build log and fallback `hdiutil` output. |
| Updater does not see the release | Release is draft, prerelease, or tag is wrong | Publish the release as latest with a normal `vX.Y.Z` tag. |
