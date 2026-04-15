#!/bin/bash
# Build script for creating EBI macOS application bundle and DMG
# Requires: Python 3, PyInstaller, wxPython

set -e  # Exit on error

cd "$(dirname "$0")"

echo "Building EBI for macOS..."
echo "Using Python: $(which python3)"
python3 --version
echo ""

# Check if PyInstaller is installed
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found. Installing..."
    python3 -m pip install pyinstaller
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install PyInstaller"
        exit 1
    fi
    echo ""
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build the application bundle
echo "Building application bundle..."
python3 setup.py

# Verify the build succeeded
if [ ! -d "dist/ebi.app" ]; then
    echo "ERROR: Build failed - ebi.app not found"
    exit 1
fi

# Rename the executable if needed
if [ -f "dist/ebi.app/Contents/MacOS/ebi.command" ]; then
    mv dist/ebi.app/Contents/MacOS/ebi.command dist/ebi.app/Contents/MacOS/ebi
fi

# Copy wrapper script
echo "Copying launcher script..."
cp ebi.command dist/ebi.app/Contents/MacOS/ebi.command || true
chmod +x dist/ebi.app/Contents/MacOS/ebi.command || true

# Create DMG
echo "Creating DMG..."
cd dist
rm -f ebi.dmg
hdiutil create -srcfolder ebi.app -volname "EQUELLA Bulk Importer" -format UDZO ebi.dmg

echo ""
echo "================================"
echo "Build complete!"
echo "Application: $(pwd)/ebi.app"
echo "DMG installer: $(pwd)/ebi.dmg"
echo "================================"
