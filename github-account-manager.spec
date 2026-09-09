import glob
import importlib.util
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

ctk_spec = importlib.util.find_spec("customtkinter")
ctk_path = str(ctk_spec.submodule_search_locations[0]) if (ctk_spec and ctk_spec.submodule_search_locations) else "customtkinter"
datas = [(ctk_path, 'customtkinter'), ('assets', 'assets')]
binaries = []
hiddenimports = [
    'github_account_manager',
    'github_account_manager.platform.windows',
    'github_account_manager.platform.macos',
    'github_account_manager.platform.linux',
]
runtime_hooks = []

tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pydantic')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

if sys.platform.startswith("linux"):
    linux_rthook = Path("packaging/hooks/pyi_rth_tcltk_linux.py").resolve()
    if linux_rthook.exists():
        runtime_hooks.append(str(linux_rthook))

    # Fast targeted discovery for Tcl/Tk and BLT shared libraries in standard library paths
    candidate_lib_dirs = [
        Path("/usr/lib/x86_64-linux-gnu"),
        Path("/usr/lib/aarch64-linux-gnu"),
        Path("/usr/lib64"),
        Path("/usr/lib"),
    ]
    patterns = ["libtcl8.6*.so*", "libtk8.6*.so*", "libBLT*.so*"]
    seen_sos = set()
    for ldir in candidate_lib_dirs:
        if ldir.is_dir():
            for pat in patterns:
                for so_file in ldir.glob(pat):
                    if so_file.is_file() and so_file.name not in seen_sos:
                        seen_sos.add(so_file.name)
                        try:
                            resolved = so_file.resolve()
                            binaries.append((str(resolved), "."))
                            if resolved.name != so_file.name:
                                binaries.append((str(so_file), "."))
                        except Exception:
                            binaries.append((str(so_file), "."))

    # Collect Tcl and Tk asset directories
    tcl_share = Path("/usr/share/tcltk")
    if tcl_share.exists():
        for tcl_dir in tcl_share.glob("tcl8*"):
            if tcl_dir.is_dir():
                datas.append((str(tcl_dir), f"_tcl_data/{tcl_dir.name}"))
                datas.append((str(tcl_dir), "_tcl_data"))
        for tk_dir in tcl_share.glob("tk8*"):
            if tk_dir.is_dir():
                datas.append((str(tk_dir), f"_tk_data/{tk_dir.name}"))
                datas.append((str(tk_dir), "_tk_data"))


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[],
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
    name='github-account-manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'] if Path('assets/icon.ico').exists() else None,
)
