#!/bin/bash

# Icon Pelikan - macOS App Builder
# This script builds a standalone macOS application bundle

echo "🦅 Building Icon Pelikan for macOS..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/
rm -rf dist/

# Build the app using PyInstaller
echo "🔨 Building app bundle..."
pyinstaller icon_pelikan.spec

# Check if build was successful
if [ -d "dist/Icon Pelikan.app" ]; then
    echo "✅ Build successful!"
    echo "📦 App bundle created at: dist/Icon Pelikan.app"
    echo ""
    echo "You can now:"
    echo "  • Open: open 'dist/Icon Pelikan.app'"
    echo "  • Move to Applications: cp -r 'dist/Icon Pelikan.app' /Applications/"
    echo ""
else
    echo "❌ Build failed!"
    exit 1
fi
