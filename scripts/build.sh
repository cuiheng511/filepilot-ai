#!/usr/bin/env bash
# Build FilePilot AI with PyInstaller
set -e

echo "🔨 Building FilePilot AI..."

# Clean previous builds
rm -rf build/ dist/ *.spec.bak

# Build
pyinstaller FilePilot.spec --noconfirm

echo "✅ Build complete!"
echo "   macOS:   dist/FilePilot/FilePilot"
echo "   Windows: dist/FilePilot/FilePilot.exe"
echo ""
echo "To create a macOS .app bundle, use: python scripts/create_app_bundle.py"
