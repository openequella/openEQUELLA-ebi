"""
Setup script for building EBI Windows executable using PyInstaller

PyInstaller is preferred over py2exe because it:
- Supports all Python 3.x versions (including 3.10+)
- Better cross-platform support (Windows, Linux, macOS)
- Easier configuration and dependency management
- Active development and maintenance

Usage:
    # Install PyInstaller (if not already installed)
    pip install pyinstaller

    # Build the executable
    python setup.py

    # Or run PyInstaller directly
    pyinstaller ebi.spec

Output:
    dist/ebi.exe - Standalone executable
"""

import sys
import os
import subprocess


def main():
    """Build EBI executable using PyInstaller"""

    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("ERROR: PyInstaller not installed.")
        print("Install with: pip install pyinstaller")
        sys.exit(1)

    # Check if spec file exists
    spec_file = os.path.join(os.path.dirname(__file__), "ebi.spec")
    if not os.path.exists(spec_file):
        print("ERROR: ebi.spec file not found")
        print("Run this script from the package-win directory")
        sys.exit(1)

    print("=" * 50)
    print("Building EQUELLA Bulk Importer with PyInstaller")
    print("=" * 50)
    print()

    # Run PyInstaller
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "ebi.spec"]
    print(f"Running: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

    if result.returncode == 0:
        print()
        print("=" * 50)
        print("Build successful!")
        print("Executable: dist/ebi.exe")
        print("=" * 50)
    else:
        print()
        print("ERROR: Build failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
