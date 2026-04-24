#!/bin/bash
# Build script for EBI Linux distribution using PyInstaller
# Creates ebi.zip containing the packaged application

echo "========================================"
echo "Building EQUELLA Bulk Importer (Linux)"
echo "========================================"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found in PATH"
    echo "Please install Python 3 and ensure it's in your PATH"
    exit 1
fi

# Check if PyInstaller is installed
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo "ERROR: PyInstaller not found"
    echo "Installing PyInstaller..."
    python3 -m pip install pyinstaller
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install PyInstaller"
        exit 1
    fi
fi

# Clean previous build artifacts
echo "Cleaning previous build..."
rm -rf dist build ebi ebi.zip

# Build with PyInstaller
echo ""
echo "Building executable with PyInstaller..."
python3 setup.py
if [ $? -ne 0 ]; then
    echo "ERROR: Build failed"
    exit 1
fi

# Check if build succeeded
if [ ! -f "dist/ebi/ebi" ]; then
    echo "ERROR: Build succeeded but dist/ebi/ebi executable not found"
    exit 1
fi

# Move built directory to ebi for distribution
echo "Preparing distribution directory..."
mv dist/ebi ebi
rmdir dist 2>/dev/null || true

# PyInstaller includes everything needed, but copy source files for reference
echo "Copying source files for reference..."
mkdir -p ebi/source
cp ../source/ebi.py ebi/source/ 2>/dev/null || true
cp ../source/MainFrame.py ebi/source/ 2>/dev/null || true
cp ../source/OptionsDialog.py ebi/source/ 2>/dev/null || true
cp ../source/Engine.py ebi/source/ 2>/dev/null || true
cp ../source/equellaclient41.py ebi/source/ 2>/dev/null || true
cp ../source/ebi.properties ebi/source/ 2>/dev/null || true

# Create zip package
echo ""
echo "Creating distribution archive..."
python3 package.py
if [ $? -ne 0 ]; then
    echo "ERROR: Packaging failed"
    exit 1
fi

# Verify zip was created
if [ ! -f "ebi.zip" ]; then
    echo "ERROR: ebi.zip was not created"
    exit 1
fi

echo ""
echo "========================================"
echo "Build complete: ebi.zip"
echo "========================================"
echo ""
