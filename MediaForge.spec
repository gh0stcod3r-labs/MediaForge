# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for MediaForge Organizer
Build command: pyinstaller MediaForge.spec
"""
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/mediaforge/constants.py', 'mediaforge'),
        ('src/mediaforge', 'mediaforge'),
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'pathlib',
        'json',
        'csv',
        'logging',
        'dataclasses',
        'typing',
        'enum',
        'threading',
        'concurrent.futures',
        'requests',
        'hashlib',
        'time',
        'urllib.parse',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MediaForge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app - no console window (set True for debugging)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if Path('icon.ico').exists() else None,
)
