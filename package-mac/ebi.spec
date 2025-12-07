# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for EQUELLA Bulk Importer (EBI) - macOS

This file defines how PyInstaller should build the EBI macOS application bundle.
It specifies all dependencies, data files, and bundle options.

Usage:
    pyinstaller ebi.spec
    
Or use the setup.py wrapper:
    python3 setup.py
"""

import os
import sys

# Get the directory containing this spec file
spec_dir = os.path.dirname(os.path.abspath(SPEC))

# Path to source files - use the main source directory, not the outdated copy
source_dir = os.path.join(os.path.dirname(spec_dir), 'source')

# Import version from ebi module
sys.path.insert(0, source_dir)
import ebi

block_cipher = None

# Collect all data files (images, icons, properties)
datas = [
    (os.path.join(source_dir, 'ebi.properties'), '.'),
    (os.path.join(source_dir, 'ebibig.ico'), '.'),
    (os.path.join(source_dir, 'ebismall.ico'), '.'),
    (os.path.join(source_dir, 'fileopen.png'), '.'),
    (os.path.join(source_dir, 'filesave.png'), '.'),
    (os.path.join(source_dir, 'gtk-stop.png'), '.'),
    (os.path.join(source_dir, 'gtk-help.png'), '.'),
    (os.path.join(source_dir, 'options.png'), '.'),
    (os.path.join(source_dir, 'pause.png'), '.'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'wx',
    'wx.grid',
    'wx.html',
    'wx.lib.wordwrap',
    'configparser',
    'html.parser',
    'xml.etree.ElementTree',
]

a = Analysis(
    [os.path.join(source_dir, 'ebi.py')],
    pathex=[source_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'test', 'unittest', 'matplotlib', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ebi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ebi',
)

app = BUNDLE(
    coll,
    name='ebi.app',
    icon=None,  # macOS requires .icns format; .ico files from Windows won't work without conversion
    bundle_identifier='org.apereo.equella.ebi',
    version=ebi.Version,
    info_plist={
        'CFBundleName': 'EQUELLA Bulk Importer',
        'CFBundleDisplayName': 'EQUELLA Bulk Importer',
        'CFBundleShortVersionString': ebi.Version,
        'CFBundleVersion': ebi.Version,
        'CFBundleIdentifier': 'org.apereo.equella.ebi',
        'NSHumanReadableCopyright': 'Copyright (c) 2024, The Apereo Foundation',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSMinimumSystemVersion': '10.13.0',
    },
)
