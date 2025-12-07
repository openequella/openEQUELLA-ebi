# macOS Packaging with PyInstaller

This directory contains scripts for building EBI application bundle and DMG for macOS using PyInstaller.

## Prerequisites

- Python 3.7 or later (including 3.13+)
- PyInstaller: `pip3 install pyinstaller`
- wxPython: `pip3 install wxPython`

## Why PyInstaller Instead of py2app?

PyInstaller was chosen over py2app because:

- **Python 3.13 compatibility**: py2app 0.28.9 fails with Python 3.13 due to removed `imp` module
- **Active development**: PyInstaller has more frequent updates
- **Cross-platform consistency**: Same build tool as Windows/Linux
- **Better dependency detection**: Automatically finds wxPython modules
- **Simpler configuration**: Easier to maintain and troubleshoot

## Building

### Quick Build (Recommended)

```bash
cd package-mac
./ebi-package.command
```

This will:
1. Check for Python 3 and PyInstaller
2. Install PyInstaller if needed
3. Clean previous builds
4. Build the application bundle
5. Create a DMG installer

### Build Application Only

```bash
cd package-mac
python3 setup.py
```

Or use PyInstaller directly:

```bash
cd package-mac
pyinstaller ebi.spec
```

### Manual DMG Creation

After building the application:

```bash
cd package-mac/dist
hdiutil create -srcfolder ebi.app -volname "EQUELLA Bulk Importer" -format UDZO ebi.dmg
hdiutil internet-enable -yes ebi.dmg
```

## Output

The build process creates:

- `dist/ebi.app` - The macOS application bundle
- `dist/ebi.dmg` - Disk image installer (if using ebi-package.command)

## Configuration

The build is configured in `ebi.spec`:

- **Source location**: `source/ebi/` directory
- **Data files**: All images, icons, and properties files
- **Hidden imports**: wxPython modules
- **Bundle identifier**: `org.apereo.equella.ebi`
- **Version**: Read from `ebi.Version`
- **Console**: Disabled (GUI application)
- **High DPI**: Enabled (`NSHighResolutionCapable`)
- **Minimum macOS**: 10.13 (High Sierra)

## Troubleshooting

### PyInstaller not found

Install it:
```bash
pip3 install pyinstaller
```

### wxPython not found

Install it:
```bash
pip3 install wxPython
```

### "No module named 'modulegraph'" or "No module named 'imp'"

This error occurs with py2app on Python 3.12+. The solution is to use PyInstaller instead (which this setup already does).

### Missing dependencies in built application

Edit `ebi.spec` and add the missing module to `hiddenimports`:
```python
hiddenimports = [
    'wx',
    'your.missing.module',
]
```

### Application won't open or crashes immediately

Test the executable directly:
```bash
cd dist/ebi.app/Contents/MacOS
./ebi
```

This will show error messages in the terminal.

### Code signing and notarization

For distribution outside development, you'll need to:

1. Sign the application:
```bash
codesign --deep --force --sign "Developer ID Application: Your Name" dist/ebi.app
```

2. Create and sign the DMG:
```bash
codesign --sign "Developer ID Application: Your Name" dist/ebi.dmg
```

3. Notarize with Apple:
```bash
xcrun notarytool submit dist/ebi.dmg --keychain-profile "AC_PASSWORD" --wait
xcrun stapler staple dist/ebi.dmg
```

## Testing

After building, test the application:

1. Open the app bundle:
```bash
open dist/ebi.app
```

2. Or mount and test the DMG:
```bash
open dist/ebi.dmg
```

## File Structure

```
package-mac/
├── ebi-package.command    # Main build script
├── setup.py               # Python build wrapper
├── ebi.spec              # PyInstaller configuration
├── ebi.command           # Launch wrapper (if needed)
└── source/
    └── ebi/              # Source files and resources
        ├── ebi.py
        ├── MainFrame.py
        ├── Engine.py
        ├── equellaclient41.py
        ├── OptionsDialog.py
        ├── ebi.properties
        └── *.png, *.ico   # Icons and images
```

## Differences from py2app

If you previously used py2app:

| Aspect | py2app | PyInstaller |
|--------|--------|-------------|
| Python 3.13 | ❌ Broken | ✅ Works |
| Configuration | setup.py | .spec file |
| Build command | `python3 setup.py py2app` | `pyinstaller ebi.spec` |
| Bundle structure | Same | Same |
| Dependencies | Manual listing | Auto-detection |
| Maintenance | Stagnant | Active |
