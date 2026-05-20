#!/usr/bin/env bash
# ==============================================================================
# FilePilot AI — Linux AppImage Build Script
#
# Usage:
#   ./scripts/build_appimage.sh                          # Full build
#   ./scripts/build_appimage.sh --skip-pyinstaller       # AppImage only (skip PyInstaller)
#   APPIMAGE_ARCH=x86_64 ./scripts/build_appimage.sh     # Specify arch
#
# Requirements:
#   - Python 3.10+ with PySide6
#   - pip install pyinstaller
#   - Docker (optional, for linuxdeploy in container)
#
# Output: dist/FilePilot-<version>-<arch>.AppImage
# ==============================================================================
set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
VERSION="$(python -c "from filepilot import __version__; print(__version__)" 2>/dev/null || echo "0.6.0")"
ARCH="${APPIMAGE_ARCH:-$(uname -m)}"
APP_NAME="FilePilot"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/dist"

SKIP_PYINSTALLER=false
[[ "${1:-}" == "--skip-pyinstaller" ]] && SKIP_PYINSTALLER=true

echo "🔨 Building FilePilot AI v$VERSION AppImage ($ARCH)"
echo ""

mkdir -p "$OUTPUT_DIR"

# ── Step 1: PyInstaller ─────────────────────────────────────────────────────
if ! $SKIP_PYINSTALLER; then
  # Pre-check: pyinstaller must be installed
  if ! command -v pyinstaller &>/dev/null; then
    echo "  ❌ pyinstaller not found. Install with: pip install pyinstaller"
    exit 1
  fi
  echo "[1/3] PyInstaller build..."

  # Clean previous builds
  rm -rf "$PROJECT_DIR/build" "$PROJECT_DIR/dist/FilePilot" "$PROJECT_DIR"/*.spec.bak

  # We need a temporary spec for Linux: no .ico, no console
  cat > "$PROJECT_DIR/FilePilot-linux.spec" << 'SPECTEMPLATE'
# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for FilePilot AI — Linux"""
import sys
sys.setrecursionlimit(10000)
block_cipher = None

a = Analysis(
    ['filepilot/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('filepilot/resources', 'filepilot/resources'),
        ('filepilot/styles/themes', 'filepilot/styles/themes'),
    ],
    hiddenimports=[
        'filepilot.ai.base', 'filepilot.ai.local_ai', 'filepilot.ai.cloud_ai',
        'filepilot.ai.summarizer', 'filepilot.app', 'filepilot.auto_start',
        'filepilot.cli', 'filepilot.i18n',
        'filepilot.log', 'filepilot.core.embeddings', 'filepilot.core.search_cache',
        'filepilot.core.file_scanner',
        'filepilot.core.duplicate_finder', 'filepilot.core.file_organizer',
        'filepilot.core.indexer', 'filepilot.core.file_watcher', 'filepilot.core.task_queue',
        'filepilot.core.config', 'filepilot.core.task_scheduler',
        'filepilot.core.tag_manager', 'filepilot.core.tag_rules', 'filepilot.core.plugin_system',
        'filepilot.core.service_container', 'filepilot.core.app_state', 'filepilot.core.event_bus',
        'filepilot.core.worker', 'filepilot.core.errors', 'filepilot.core.index_db',
        'filepilot.extractors.pdf_extractor',
        'filepilot.extractors.markdown_extractor', 'filepilot.extractors.code_extractor',
        'filepilot.extractors.image_extractor', 'filepilot.extractors.ocr_extractor',
        'filepilot.extractors.docx_extractor',
        'filepilot.extractors.xlsx_extractor', 'filepilot.extractors.pptx_extractor',
        'filepilot.utils.file_utils', 'filepilot.ui.tray', 'filepilot.ui.tags_panel',
        'filepilot.ui.plugin_manager_panel', 'filepilot.ui.dashboard_panel', 'filepilot.ui.notification',
        'filepilot.ui.preview_panel', 'filepilot.ui.directory_tree', 'filepilot.styles.manager',
        'whoosh', 'whoosh.fields', 'whoosh.index', 'whoosh.qparser',
        'fitz', 'PIL', 'markdown', 'yaml', 'cryptography',
        'docx', 'openpyxl', 'pptx', 'send2trash', 'watchdog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy', 'pandas', 'torch', 'tensorflow'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='FilePilot', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None,
    entitlements_file=None, icon=None,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[], name='FilePilot',
)
SPECTEMPLATE

  cd "$PROJECT_DIR"
  pyinstaller FilePilot-linux.spec --noconfirm
  rm -f FilePilot-linux.spec

  if [ ! -d "$OUTPUT_DIR/FilePilot" ]; then
    echo "  ❌ PyInstaller build failed — dist/FilePilot not found"
    exit 1
  fi

  SIZE=$(du -sh "$OUTPUT_DIR/FilePilot" | cut -f1)
  echo "  ✅ PyInstaller OK — $SIZE"
else
  echo "[1/3] PyInstaller build skipped (--skip-pyinstaller)"
  if [ ! -d "$OUTPUT_DIR/FilePilot" ]; then
    echo "  ❌ No existing build at dist/FilePilot. Cannot skip PyInstaller."
    exit 1
  fi
fi

# ── Step 2: AppDir preparation ──────────────────────────────────────────────
echo ""
echo "[2/3] Preparing AppDir..."

APPDIR="$OUTPUT_DIR/$APP_NAME.AppDir"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APPDIR/usr/share/metainfo"

# Copy PyInstaller build
cp -r "$OUTPUT_DIR/FilePilot"/* "$APPDIR/usr/bin/"
rm -rf "$APPDIR/usr/bin/__pycache__" 2>/dev/null || true

# Main executable symlink
ln -sf "usr/bin/FilePilot" "$APPDIR/AppRun"
cat > "$APPDIR/AppRun" << 'APPRUN'
#!/usr/bin/env bash
# FilePilot AI — AppRun
APPDIR="$(dirname "$(readlink -f "$0")")"
export PATH="$APPDIR/usr/bin:$PATH"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:$LD_LIBRARY_PATH"
export QT_QPA_PLATFORM_PLUGIN_PATH="$APPDIR/usr/bin/PySide6/Qt/plugins"
exec "$APPDIR/usr/bin/FilePilot" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# Desktop file
cat > "$APPDIR/usr/share/applications/io.github.filepilot.desktop" << DESKTOP
[Desktop Entry]
Name=FilePilot AI
Comment=AI-powered file management tool
Exec=FilePilot
Icon=io.github.filepilot
Type=Application
Categories=Utility;FileManager;Office;
Terminal=false
StartupNotify=true
X-AppImage-Version=$VERSION
DESKTOP

# Copy the desktop file to root of AppDir
cp "$APPDIR/usr/share/applications/io.github.filepilot.desktop" "$APPDIR/"

# App icon — use the existing PNG
if [ -f "$PROJECT_DIR/filepilot/resources/app.png" ]; then
  cp "$PROJECT_DIR/filepilot/resources/app.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/io.github.filepilot.png"
  cp "$PROJECT_DIR/filepilot/resources/app.png" "$APPDIR/io.github.filepilot.png"
  echo "  ✅ Icon copied"
else
  echo "  ⚠  app.png not found, using placeholder"
fi

# AppStream metainfo
cat > "$APPDIR/usr/share/metainfo/io.github.filepilot.appdata.xml" << APPDATA
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>io.github.filepilot</id>
  <name>FilePilot AI</name>
  <summary>AI-powered file management tool</summary>
  <description>
    <p>FilePilot AI is a desktop application that helps you manage, organize,
    search, and analyze files using AI-powered features.</p>
  </description>
  <launchable type="desktop-id">io.github.filepilot.desktop</launchable>
  <url type="homepage">https://github.com/cuiheng511/filepilot-ai</url>
  <project_license>MIT</project_license>
  <metadata_license>MIT</metadata_license>
  <content_rating type="oars-1.1" />
  <developer id="io.github.cuiheng511">
    <name>cuiheng511</name>
  </developer>
  <releases>
    <release version="$VERSION" date="$(date +%Y-%m-%d)"/>
  </releases>
</component>
APPDATA

echo "  ✅ AppDir prepared at $APPDIR"

# ── Step 3: Build AppImage ──────────────────────────────────────────────────
echo ""
echo "[3/3] Building AppImage..."

# Try to find appimagetool
APPIMAGETOOL=""
if command -v appimagetool &>/dev/null; then
  APPIMAGETOOL="appimagetool"
elif [ -f "$PROJECT_DIR/.tools/appimagetool" ]; then
  APPIMAGETOOL="$PROJECT_DIR/.tools/appimagetool"
else
  # Download appimagetool
  echo "  Downloading appimagetool..."
  mkdir -p "$PROJECT_DIR/.tools"
  APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-$(uname -m).AppImage"
  if command -v wget &>/dev/null; then
    wget -q -O "$PROJECT_DIR/.tools/appimagetool" "$APPIMAGETOOL_URL"
  elif command -v curl &>/dev/null; then
    curl -sL -o "$PROJECT_DIR/.tools/appimagetool" "$APPIMAGETOOL_URL"
  else
    echo "  ❌ Neither wget nor curl found. Please install appimagetool manually."
    echo "     https://github.com/AppImage/AppImageKit/releases"
    echo "  📁  AppDir ready at: $APPDIR"
    exit 0
  fi
  chmod +x "$PROJECT_DIR/.tools/appimagetool"
  APPIMAGETOOL="$PROJECT_DIR/.tools/appimagetool"
fi

# Set FUSE magic skip for containers/CI
APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGETOOL" "$APPDIR" "$OUTPUT_DIR/${APP_NAME}-${VERSION}-${ARCH}.AppImage"

if [ -f "$OUTPUT_DIR/${APP_NAME}-${VERSION}-${ARCH}.AppImage" ]; then
  SIZE=$(du -h "$OUTPUT_DIR/${APP_NAME}-${VERSION}-${ARCH}.AppImage" | cut -f1)
  echo ""
  echo "✅ Build complete!"
  echo "   📦 $OUTPUT_DIR/${APP_NAME}-${VERSION}-${ARCH}.AppImage ($SIZE)"
  echo ""
  echo "   Run: $OUTPUT_DIR/${APP_NAME}-${VERSION}-${ARCH}.AppImage"
else
  echo ""
  echo "  ⚠  AppImage not created — appimagetool may have failed."
  echo "  📁  AppDir ready at: $APPDIR"
fi

# Cleanup temp spec
rm -f "$PROJECT_DIR"/*.spec.bak
