#!/usr/bin/env bash
# ==============================================================================
# FilePilot AI — macOS Build Script
#
# Builds a .app bundle with PyInstaller, optionally signs it, and wraps it
# in a .dmg using create-dmg.
#
# Usage:
#   ./scripts/build_macos.sh                          # Full build (app + dmg)
#   ./scripts/build_macos.sh --app-only                # .app only, no .dmg
#   ./scripts/build_macos.sh --skip-pyinstaller        # Only create .dmg
#   ./scripts/build_macos.sh --sign                    # Sign the .app
#   ./scripts/build_macos.sh --notarize                # Notarize (implies --sign)
#
# Requirements:
#   - macOS 12+ with Xcode Command Line Tools
#   - Python 3.10+ with PySide6
#   - pip install pyinstaller
#   - brew install create-dmg   (for .dmg creation)
#   - For signing: Apple Developer certificate in keychain
#
# Output:
#   dist/FilePilot.app
#   dist/FilePilot-<version>.dmg
# ==============================================================================
set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
VERSION="$(python -c "from filepilot import __version__; print(__version__)" 2>/dev/null || echo "0.4.0")"
APP_NAME="FilePilot"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/dist"
BUNDLE_NAME="${APP_NAME}.app"
BUNDLE_PATH="$OUTPUT_DIR/$BUNDLE_NAME"

DO_APP_ONLY=false
SKIP_PYINSTALLER=false
DO_SIGN=false
DO_NOTARIZE=false

for arg in "$@"; do
  case "$arg" in
    --app-only) DO_APP_ONLY=true ;;
    --skip-pyinstaller) SKIP_PYINSTALLER=true ;;
    --sign) DO_SIGN=true ;;
    --notarize) DO_NOTARIZE=true; DO_SIGN=true ;;
  esac
done

echo "🔨 Building FilePilot AI v$VERSION for macOS"
echo ""

mkdir -p "$OUTPUT_DIR"

# ── Step 1: Generate .icns icon if needed ───────────────────────────────────
if [ ! -f "$PROJECT_DIR/filepilot/resources/app.icns" ] && [ -f "$PROJECT_DIR/filepilot/resources/app.png" ]; then
  echo "[0/4] Generating .icns icon from app.png..."
  ICON_DIR="$PROJECT_DIR/.tmp/icons.iconset"
  mkdir -p "$ICON_DIR"

  # Generate all required sizes
  for size in 16 32 64 128 256 512; do
    sips -z "$size" "$size" \
      "$PROJECT_DIR/filepilot/resources/app.png" \
      --out "$ICON_DIR/icon_${size}x${size}.png" &>/dev/null || true
    # Retina sizes (2x)
    if [ "$size" -le 256 ]; then
      sips -z "$((size*2))" "$((size*2))" \
        "$PROJECT_DIR/filepilot/resources/app.png" \
        --out "$ICON_DIR/icon_${size}x${size}@2x.png" &>/dev/null || true
    fi
  done

  iconutil -c icns "$ICON_DIR" -o "$PROJECT_DIR/filepilot/resources/app.icns" 2>/dev/null && \
    echo "  ✅ Generated app.icns" || \
    echo "  ⚠  iconutil not available (non-macOS). icns generation skipped."

  rm -rf "$PROJECT_DIR/.tmp/icons.iconset"
fi

# ── Step 2: PyInstaller ─────────────────────────────────────────────────────
if ! $SKIP_PYINSTALLER; then
  # Pre-check: pyinstaller must be installed
  if ! command -v pyinstaller &>/dev/null; then
    echo "  ❌ pyinstaller not found. Install with: pip install pyinstaller"
    exit 1
  fi
  echo "[1/4] PyInstaller build..."

  rm -rf "$PROJECT_DIR/build" "$BUNDLE_PATH" "$PROJECT_DIR"/*.spec.bak

  ICON_PATH=""
  if [ -f "$PROJECT_DIR/filepilot/resources/app.icns" ]; then
    ICON_PATH="$PROJECT_DIR/filepilot/resources/app.icns"
  fi

  # Build as one-dir .app bundle (macOS specific)
  pyinstaller \
    --noconfirm \
    --clean \
    --name "$APP_NAME" \
    --windowed \
    --onedir \
    --add-data "filepilot/resources:filepilot/resources" \
    --add-data "filepilot/styles/themes:filepilot/styles/themes" \
    --hidden-import "filepilot.ai.base" \
    --hidden-import "filepilot.ai.local_ai" \
    --hidden-import "filepilot.ai.cloud_ai" \
    --hidden-import "filepilot.ai.summarizer" \
    --hidden-import "filepilot.app" \
    --hidden-import "filepilot.cli" \
    --hidden-import "filepilot.i18n" \
    --hidden-import "filepilot.log" \
    --hidden-import "filepilot.core.search_cache" \
    --hidden-import "filepilot.core.file_scanner" \
    --hidden-import "filepilot.core.duplicate_finder" \
    --hidden-import "filepilot.core.file_organizer" \
    --hidden-import "filepilot.core.indexer" \
    --hidden-import "filepilot.core.file_watcher" \
    --hidden-import "filepilot.core.task_queue" \
    --hidden-import "filepilot.core.config" \
    --hidden-import "filepilot.extractors.pdf_extractor" \
    --hidden-import "filepilot.extractors.markdown_extractor" \
    --hidden-import "filepilot.extractors.code_extractor" \
    --hidden-import "filepilot.extractors.image_extractor" \
    --hidden-import "filepilot.extractors.docx_extractor" \
    --hidden-import "filepilot.extractors.xlsx_extractor" \
    --hidden-import "filepilot.extractors.pptx_extractor" \
    --hidden-import "filepilot.utils.file_utils" \
    --hidden-import "filepilot.ui.tray" \
    --hidden-import "filepilot.styles.manager" \
    --hidden-import "whoosh" \
    --hidden-import "whoosh.fields" \
    --hidden-import "whoosh.index" \
    --hidden-import "whoosh.qparser" \
    --hidden-import "fitz" \
    --hidden-import "PIL" \
    --hidden-import "markdown" \
    --hidden-import "yaml" \
    --hidden-import "cryptography" \
    --hidden-import "docx" \
    --hidden-import "openpyxl" \
    --hidden-import "pptx" \
    --hidden-import "send2trash" \
    --hidden-import "watchdog" \
    --exclude-module "tkinter" \
    --exclude-module "matplotlib" \
    --exclude-module "scipy" \
    --exclude-module "pandas" \
    --exclude-module "torch" \
    --exclude-module "tensorflow" \
    ${ICON_PATH:+--icon "$ICON_PATH"} \
    "$PROJECT_DIR/filepilot/main.py"

  # PyInstaller --onedir places the .app in dist/
  if [ ! -d "$BUNDLE_PATH" ]; then
    # Also check if PyInstaller placed it elsewhere
    if [ -d "$OUTPUT_DIR/$BUNDLE_NAME" ]; then
      BUNDLE_PATH="$OUTPUT_DIR/$BUNDLE_NAME"
    else
      echo "  ❌ .app bundle not found"
      ls -la "$OUTPUT_DIR/" 2>/dev/null || true
      exit 1
    fi
  fi

  SIZE=$(du -sh "$BUNDLE_PATH" | cut -f1)
  echo "  ✅ PyInstaller OK — $SIZE ($BUNDLE_PATH)"
else
  echo "[1/4] PyInstaller build skipped (--skip-pyinstaller)"
  if [ ! -d "$BUNDLE_PATH" ]; then
    echo "  ❌ No existing .app at $BUNDLE_PATH. Cannot skip."
    exit 1
  fi
fi

# ── Step 3: Code signing (optional) ─────────────────────────────────────────
if $DO_SIGN; then
  echo ""
  echo "[2/4] Signing .app bundle..."

  # Attempt to find the Developer ID Application certificate
  SIGN_IDENTITY="${SIGN_IDENTITY:-$(security find-identity -v -p codesigning 2>/dev/null | grep "Developer ID Application" | head -1 | grep -oE '"[^"]+"' | tr -d '"' || echo "")}"

  if [ -z "$SIGN_IDENTITY" ]; then
    # Fall back to "Developer ID Application" wildcard
    SIGN_IDENTITY="Developer ID Application"
  fi

  echo "  Using identity: $SIGN_IDENTITY"

  # Sign individual libraries first, then the .app bundle (--deep handles frameworks)
  find "$BUNDLE_PATH" -type f \( -name "*.dylib" -o -name "*.so" \) -print0 2>/dev/null | \
    xargs -0 -I {} codesign --force --options runtime --sign "$SIGN_IDENTITY" "{}" 2>/dev/null || true

  # Sign the .app (--deep signs nested frameworks automatically)
  codesign --force --options runtime --deep --sign "$SIGN_IDENTITY" "$BUNDLE_PATH" 2>&1
  echo "  ✅ Code signing complete"

  # Verify
  codesign -dv --verbose=2 "$BUNDLE_PATH" 2>&1 | head -5
else
  echo ""
  echo "[2/4] Code signing skipped (use --sign to enable)"
fi

# ── Step 4: Notarization (optional) ─────────────────────────────────────────
if $DO_NOTARIZE; then
  echo ""
  echo "[3/4] Notarizing with Apple..."

  # Create a zip for notarization
  NOTARIZE_ZIP="$OUTPUT_DIR/${APP_NAME}-notarize.zip"
  ditto -c -k --keepParent "$BUNDLE_PATH" "$NOTARIZE_ZIP"

  # Submit for notarization
  # Requires: AC_USERNAME (Apple ID) and AC_PASSWORD (app-specific password) or AC_API_KEY
  xcrun notarytool submit "$NOTARIZE_ZIP" \
    --apple-id "${AC_USERNAME:-}" \
    --team-id "${AC_TEAM_ID:-}" \
    --password "${AC_PASSWORD:-}" \
    --wait 2>&1 || echo "  ⚠  Notarization failed. Check credentials."

  # Staple the ticket to the .app
  xcrun stapler staple "$BUNDLE_PATH" 2>&1 || true

  rm -f "$NOTARIZE_ZIP"
  echo "  ✅ Notarization complete"
else
  echo ""
  echo "[3/4] Notarization skipped (use --notarize to enable)"
fi

# ── Step 5: Create .dmg ────────────────────────────────────────────────────
if $DO_APP_ONLY; then
  echo ""
  echo "[4/4] Skipping DMG creation (--app-only)"
  echo ""
  echo "✅ Build complete!"
  echo "   📁 $BUNDLE_PATH"
else
  echo ""
  echo "[4/4] Creating DMG..."

  DMG_NAME="${APP_NAME}-${VERSION}.dmg"
  DMG_PATH="$OUTPUT_DIR/$DMG_NAME"
  DMG_DIR="$OUTPUT_DIR/.dmg-source"

  # Clean up previous DMG
  rm -rf "$DMG_PATH" "$DMG_DIR"
  mkdir -p "$DMG_DIR"
  cp -R "$BUNDLE_PATH" "$DMG_DIR/"
  ln -s /Applications "$DMG_DIR/Applications" 2>/dev/null || true

  # Use create-dmg if available, else hdiutil directly
  if command -v create-dmg &>/dev/null; then
    create-dmg \
      --volname "$APP_NAME" \
      --volicon "$PROJECT_DIR/filepilot/resources/app.icns" \
      --window-pos 200 120 \
      --window-size 800 400 \
      --icon-size 100 \
      --icon "$APP_NAME.app" 200 190 \
      --hide-extension "$APP_NAME.app" \
      --app-drop-link 600 185 \
      --no-internet-enable \
      "$DMG_PATH" \
      "$DMG_DIR" 2>&1 || true
  else
    echo "  create-dmg not found, using hdiutil..."
    echo "  Install with: brew install create-dmg"

    # Fallback: basic DMG with hdiutil + rsync
    hdiutil create -volname "$APP_NAME" \
      -srcfolder "$DMG_DIR" \
      -ov -format UDZO \
      -imagekey zlib-level=9 \
      "$DMG_PATH"
  fi

  # Set the icon on the DMG
  if [ -f "$PROJECT_DIR/filepilot/resources/app.icns" ]; then
    # Mount, set icon, unmount
    MOUNT_POINT="/Volumes/$APP_NAME"
    if [ -d "$MOUNT_POINT" ]; then
      hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || true
    fi
    hdiutil attach "$DMG_PATH" -quiet -nobrowse 2>/dev/null || true
    if [ -d "$MOUNT_POINT" ]; then
      cp "$PROJECT_DIR/filepilot/resources/app.icns" "$MOUNT_POINT/.VolumeIcon.icns" 2>/dev/null || true
      SetFile -c icnC "$MOUNT_POINT/.VolumeIcon.icns" 2>/dev/null || true
      SetFile -a C "$MOUNT_POINT" 2>/dev/null || true
      hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || true
    fi
  fi

  if [ -f "$DMG_PATH" ]; then
    SIZE=$(du -h "$DMG_PATH" | cut -f1)
    rm -rf "$DMG_DIR"
    echo ""
    echo "✅ Build complete!"
    echo "   📁 Bundle: $BUNDLE_PATH"
    echo "   📦 DMG:    $DMG_PATH ($SIZE)"
  else
    echo ""
    echo "⚠ DMG creation failed. Bundle is at: $BUNDLE_PATH"
  fi
fi

# Cleanup
rm -f "$PROJECT_DIR"/*.spec.bak
