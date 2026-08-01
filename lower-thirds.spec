# PyInstaller spec for Lower Thirds (PyQt6).
# Build on each target OS — Qt apps cannot be cross-compiled.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None

project_root = Path(SPECPATH)
entry_point = project_root / "lower_thirds" / "app.py"

pyqt6_datas, pyqt6_binaries, pyqt6_hiddenimports = collect_all("PyQt6")

a = Analysis(
    [str(entry_point)],
    pathex=[str(project_root)],
    binaries=pyqt6_binaries,
    datas=[
        (str(project_root / "data" / "example.json"), "data"),
        *pyqt6_datas,
    ],
    hiddenimports=[
        *pyqt6_hiddenimports,
        "lower_thirds",
        "lower_thirds.app",
        "lower_thirds.main_window",
        "lower_thirds.lower_third_display",
        "lower_thirds.participant_list",
        "lower_thirds.data_store",
        "lower_thirds.models",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="lower-thirds",
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
    name="lower-thirds",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Lower Thirds.app",
        icon=None,
        bundle_identifier="dev.lower-thirds.app",
        info_plist={
            "CFBundleDisplayName": "Lower Thirds",
            "CFBundleName": "Lower Thirds",
            "NSHighResolutionCapable": True,
        },
    )
