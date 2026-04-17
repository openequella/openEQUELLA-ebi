"""
Setup script for building EBI macOS application bundle using PyInstaller

PyInstaller is used instead of py2app because:
- Better Python 3.13+ support (py2app fails with Python 3.13)
- Active development and maintenance
- Consistent build process across platforms

Usage:
    python3 setup.py
    
Or directly:
    pyinstaller ebi.spec
"""

import sys
import os
import subprocess

def main():
    """Build EBI macOS application using PyInstaller"""
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("ERROR: PyInstaller not installed.")
        print("Install with: pip3 install pyinstaller")
        sys.exit(1)
    
    # Check if spec file exists
    spec_file = os.path.join(os.path.dirname(__file__), 'ebi.spec')
    if not os.path.exists(spec_file):
        print("ERROR: ebi.spec file not found")
        print("Run this script from the package-mac directory")
        sys.exit(1)
    
    print("="*50)
    print("Building EQUELLA Bulk Importer for macOS")
    print("="*50)
    print()
    
    # Run PyInstaller
    cmd = [sys.executable, '-m', 'PyInstaller', '--clean', 'ebi.spec']
    print(f"Running: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, cwd=os.path.abspath(os.path.dirname(__file__)))
    
    if result.returncode == 0:
        print()
        print("="*50)
        print("Build successful!")
        print("Application: dist/ebi.app")
        print("="*50)
    else:
        print()
        print("ERROR: Build failed")
        sys.exit(1)

if __name__ == '__main__':
    main()
