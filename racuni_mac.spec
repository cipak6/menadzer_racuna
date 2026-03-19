# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('assets/DejaVuSansMono.ttf', 'assets')]
binaries = []
hiddenimports = []

for pkg in ['customtkinter', 'requests', 'bs4', 'lxml', 'openpyxl',
            'srtools', 'pymupdf', 'PIL', 'qrcode']:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

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
        'fitz',
        'qrcode',
        'qrcode.image.pil',
        'qrcode.image.pure',
        'qrcode.constants',
        'qrcode.main',
        'zxingcpp',
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
    upx=False,
    console=False,
    windowed=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='Racuni',
)

app = BUNDLE(
    coll,
    name='Racuni.app',
    icon=None,
    bundle_identifier='com.cipak.racuni',
)