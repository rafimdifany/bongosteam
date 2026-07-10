# -*- mode: python -*-
import sys, os
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['bongo_steam/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/skins', 'assets/skins'),
        ('assets/controllers', 'assets/controllers'),
    ],
    hiddenimports=[
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'pynput.keyboard._win32', 'pynput.mouse._win32',
        'pygame', 'pygame.joystick',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter'],
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='BongoSteam',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/bongo-steam.ico',
    uac_admin=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)