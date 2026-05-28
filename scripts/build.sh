#!/usr/bin/env bash
# ==============================================================================
# FilePilot AI — Unified Build Script
#
# Cross-platform build entry point. Detects OS and dispatches to the
# appropriate platform-specific build script.
#
# Usage:
#   ./scripts/build.sh                          # Build for current platform
#   ./scripts/build.sh --skip-installer         # PyInstaller only (Win)
#   ./scripts/build.sh --app-only               # .app only (macOS)
#   ./scripts/build.sh --sign                   # Sign the build (macOS)
#   ./scripts/build.sh --docker-linux           # Build Linux AppImage on any OS
#
# Output (varies by platform):
#   Windows:  dist/FilePilot-AI-Setup-*.exe
#   Linux:    dist/FilePilot-<version>-<arch>.AppImage
#   macOS:    dist/FilePilot-<version>.dmg  (+ dist/FilePilot.app)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔨 FilePilot AI — Cross-platform Build Script"
echo ""

# ── Detect OS ───────────────────────────────────────────────────────────────
case "$(uname -s)" in
  Linux*)
    OS="linux"
    BUILD_SCRIPT="$SCRIPT_DIR/build_appimage.sh"
    ;;
  Darwin*)
    OS="macos"
    BUILD_SCRIPT="$SCRIPT_DIR/build_macos.sh"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    OS="windows"
    # Embedded Windows build logic (avoid self-recursion)
    echo "🚀 Building on Windows: PyInstaller + Inno Setup..."
    echo ""
    SKIP_ARG=""
    for arg in "$@"; do
      [[ "$arg" == "--skip-installer" ]] && SKIP_ARG="--skip"
    done
    cd "$PROJECT_DIR"
    # Clean previous builds
    rm -rf build/ dist/FilePilot/ *.spec.bak
    # Step 1: PyInstaller
    echo "[1/2] PyInstaller build..."
    if ! command -v pyinstaller &>/dev/null; then
      echo "  ❌ pyinstaller not found. Install with: pip install pyinstaller"
      exit 1
    fi
    pyinstaller FilePilot.spec --noconfirm
    EXE="dist/FilePilot/FilePilot.exe"
    if [ -f "$EXE" ]; then
      SIZE=$(du -h "$EXE" | cut -f1)
      echo "  ✅ $EXE ($SIZE)"
    else
      echo "  ❌ Build failed — FilePilot.exe not found"
      exit 1
    fi
    # Step 2: Inno Setup installer
    if [ -z "$SKIP_ARG" ]; then
      echo ""
      echo "[2/2] Compiling Inno Setup installer..."
      ISCC_PATH="${ISCC_PATH:-}"
      if [ -z "$ISCC_PATH" ]; then
        for p in \
          "/c/Program Files (x86)/Inno Setup 6/ISCC.exe" \
          "/c/Program Files/Inno Setup 6/ISCC.exe" \
          "/c/Program Files (x86)/Inno Setup 5/ISCC.exe" \
          "/c/Program Files/Inno Setup 5/ISCC.exe"; do
          [ -f "$p" ] && { ISCC_PATH="$p"; break; }
        done
      fi
      if [ -n "$ISCC_PATH" ]; then
        VERSION="$(python -c "from filepilot import __version__; print(__version__)" 2>/dev/null || echo "0.6.4")"
        "$ISCC_PATH" "/dMyAppVersion=$VERSION" scripts/filepilot-installer.iss
        echo "✅ Installer built!"
      else
        echo "  ⚠ Inno Setup not found. Binaries at: dist/FilePilot/"
      fi
    else
      echo "  ℹ  --skip-installer flag set. Skipping installer."
    fi
    echo ""
    echo "✅ Build complete!"
    exit 0
    ;;
  *)
    echo "❌ Unknown OS: $(uname -s)"
    echo "   Supported: Linux, macOS, Windows"
    exit 1
    ;;
esac

echo "📋 Detected OS: $OS"
echo ""

# ── Special: Docker-based Linux build from any OS ──────────────────────────
if [[ "${1:-}" == "--docker-linux" ]]; then
  if command -v docker &>/dev/null; then
    echo "🐳 Building Linux AppImage via Docker..."
    cd "$PROJECT_DIR"
    mkdir -p "$PROJECT_DIR/.tmp"

    cat > "$PROJECT_DIR/.tmp/Dockerfile.build" << 'DOCKERFILE'
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && apt-get install -y -qq \
    python3 python3-pip python3-venv \
    libegl1 libgl1 libxkbcommon-x11-0 libxcb-cursor0 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
    libxcb-render-util0 libxcb-shape0 libxcb-xfixes0 \
    libxcb-xinerama0 libxcb-xkb1 libxcb-xv0 libxrender1 \
    fuse libfuse2 desktop-file-utils \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --upgrade pip
WORKDIR /build
COPY . .
RUN pip install -e . && pip install pyinstaller
RUN chmod +x scripts/build_appimage.sh && scripts/build_appimage.sh
DOCKERFILE

    docker build -t filepilot-linux-builder -f .tmp/Dockerfile.build .
    docker run --rm -v "$PROJECT_DIR/dist:/build/dist" filepilot-linux-builder
    echo "✅ Docker build complete. Artifacts in dist/"
  else
    echo "❌ Docker not found. Install Docker or build natively on Linux."
    exit 1
  fi
  exit 0
fi

# ── Dispatch to platform-specific script ────────────────────────────────────
case "$OS" in
  linux)
    echo "🚀 Running Linux AppImage builder..."
    exec bash "$BUILD_SCRIPT" "$@"
    ;;
  macos)
    echo "🚀 Running macOS .app/.dmg builder..."
    exec bash "$BUILD_SCRIPT" "$@"
    ;;
  windows)
    # Already handled above — this case should not be reached
    echo "❌ Unexpected branch. Exiting."
    exit 1
    ;;
esac
