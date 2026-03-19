# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas=[('assets/DejaVuSansMono.ttf', 'assets')]
binaries = []
hiddenimports = []

for pkg in ['customtkinter', 'requests', 'bs4', 'lxml', 'openpyxl', 
            'srtools', 'fitz', 'pymupdf', 'zxingcpp', 'PIL', 'qrcode', 'zxingcpp']:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        'customtkinter',
        'PIL._tkinter_finder',
        'lxml.etree',
        'lxml._elementpath',
        'tkinter',
        'tkinter.ttk',
        '_tkinter',
        'qrcode',
        'qrcode.image.pure',
        'qrcode.image.svg',
        'qrcode.image.pil',
        'qrcode.constants',
        'qrcode.main',
        'zxing_cpp',
    ],
    hookspath=[],
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
    name='Racuni',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    windowed=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='Racuni',
)