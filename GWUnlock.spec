# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


root = Path(SPECPATH)
datas = []
binaries = []
hiddenimports = []

for package in ("gnwmanager", "pyocd"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

datas += [
    (str(root / "steps"), "steps"),
    (str(root / "tools"), "tools"),
    (str(root / "resources" / "logo.ico"), "resources"),
    (str(root / "resources" / "logo.png"), "resources"),
    (str(root / "vendor"), "vendor"),
    (str(root / "upstream" / "openocd"), "upstream/openocd"),
    (str(root / "upstream" / "payload"), "upstream/payload"),
    (str(root / "upstream" / "prebuilt"), "upstream/prebuilt"),
    (str(root / "upstream" / "python"), "upstream/python"),
    (str(root / "upstream" / "shasums"), "upstream/shasums"),
]

a = Analysis(
    [str(root / "GWServiceTool.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["cmsis_pack_manager"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GWUnlock",
    icon=str(root / "resources" / "logo.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=".",
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
