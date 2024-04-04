# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['cryptoQuant.py'],
    pathex=[],
    binaries=[],
    datas=[ ( './config.json', '.' )],
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
    name='cryptoQuant',
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
    name='cryptoQuant',
)
app = BUNDLE(
    coll,
    name='cryptoQuant.app',
    icon=None,
    bundle_identifier=None,
)
