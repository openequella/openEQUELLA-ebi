# Windows/Linux Packaging with PyInstaller

This directory contains scripts for building EBI executable for Windows (and potentially Linux) using PyInstaller.

## Prerequisites

- Python 3.7 or later (including 3.10, 3.11, 3.12, 3.13, 3.14+)
- PyInstaller: `pip install pyinstaller`
- wxPython: `pip install wxPython`

## Why PyInstaller?

PyInstaller was chosen over py2exe because:

- **Better Python 3 support**: Works with all Python 3.x versions (py2exe only supports up to 3.9)
- **Cross-platform**: Can build for Windows, Linux, and macOS
- **Active development**: Regular updates and bug fixes
- **Easier configuration**: Simple spec file format
- **Better dependency detection**: Automatically finds most dependencies

## Building

### Option 1: Using the batch file (Windows)

```batch
cd package-win-linux
package.bat
```

This will:
1. Check for Python 3 and PyInstaller
2. Install PyInstaller if needed
3. Clean previous builds
4. Build the executable using PyInstaller
5. Create the distribution package (ebi.zip)

### Option 2: Using the Python setup script

```bash
cd package-win-linux
python setup.py
```

### Option 3: Using PyInstaller directly

```bash
cd package-win-linux
pyinstaller ebi.spec
```

## Output

The build process creates:

- `dist/ebi.exe` - The standalone executable
- `ebi.zip` - Distribution package containing the executable and source files

## Configuration

The build is configured in `ebi.spec`:

- **Data files**: All images, icons, and properties files are included
- **Hidden imports**: wxPython modules that PyInstaller might miss
- **Exclusions**: Unused modules (tkinter, test, unittest, etc.)
- **Console**: Disabled (GUI application)
- **Icon**: Uses ebismall.ico
- **UPX**: Enabled for compression

## Troubleshooting

### PyInstaller not found

Install it:
```bash
pip install pyinstaller
```

### Missing dependencies in built executable

Edit `ebi.spec` and add the missing module to `hiddenimports`:
```python
hiddenimports = [
    'wx',
    'your.missing.module',
]
```

### Executable too large

The executable includes Python, wxPython, and all dependencies. Typical size is 50-100 MB.
To reduce size:
- Enable UPX compression (already enabled in spec file)
- Use `--onefile` mode (already configured)
- Exclude unused modules in the `excludes` list

### Testing the executable

After building, test the executable:
```bash
cd dist
ebi.exe
```

Or from the renamed distribution:
```bash
cd ebi
ebi.exe
```

## Linux Support

PyInstaller can also build for Linux:

```bash
cd package-win-linux
python setup.py
```

The output will be `dist/ebi` (no .exe extension on Linux).

## Version Information

To add Windows version information to the executable:

1. Create a version info file using `pyi-grab_version` or manually
2. Edit `ebi.spec` and set `version_file` parameter
3. Rebuild

Example:
```python
exe = EXE(
    ...
    version_file='version_info.txt',
)
```
