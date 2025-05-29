# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# Get the current directory
current_dir = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icon_pelikan.png', 'assets'),
        ('assets/icon_pelikan.icns', 'assets'),
        ('assets/noise.png', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Icon Pelikan',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Icon Pelikan',
)

app = BUNDLE(
    coll,
    name='Icon Pelikan.app',
    icon='assets/icon_pelikan.icns',  # This sets the app icon
    bundle_identifier='com.pelikan.iconpelikan',
    version='1.0.0',
    info_plist={
        'CFBundleName': 'Icon Pelikan',
        'CFBundleDisplayName': 'Icon Pelikan',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleIdentifier': 'com.pelikan.iconpelikan',
        'LSMinimumSystemVersion': '10.15.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'NSAppleEventsUsageDescription': 'Icon Pelikan may need access to system events.',
        'NSDocumentTypes': [
            {
                'CFBundleTypeName': 'Image',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': [
                    'public.image',
                    'public.png',
                    'public.jpeg',
                    'com.compuserve.gif'
                ],
                'LSHandlerRank': 'Default'
            }
        ]
    },
)
