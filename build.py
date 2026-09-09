"""Universal Cross-Platform Build & Packaging Script producing Single-File Standalone Executables."""
import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
from typing import Optional
import zipfile

# Ensure stdout/stderr handles UTF-8 safely without crashing on CP1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import importlib.util


def _get_customtkinter_path() -> Path:
    try:
        spec = importlib.util.find_spec("customtkinter")
        if spec and spec.submodule_search_locations:
            return Path(spec.submodule_search_locations[0])
    except Exception:
        pass
    return Path("customtkinter")


def get_target_platform() -> str:
    system = platform.system().lower()
    if "windows" in system:
        return "windows"
    elif "darwin" in system:
        return "macos"
    elif "linux" in system:
        return "linux"
    return "linux"


def clean_build_artifacts():
    print("[CLEAN] Cleaning previous build artifacts...")
    for folder in ["build", "dist"]:
        p = Path(folder)
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


# Add src to sys.path to access centralized version
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from github_account_manager.version import get_version, set_version


def run_pyinstaller(target_os: str, version_override: Optional[str] = None):
    effective_override = version_override or os.environ.get("APP_VERSION_OVERRIDE")
    if effective_override:
        set_version(effective_override)

    version = get_version()
    print(f"[BUILD] Packaging Single Standalone Executable for {target_os.upper()} (Version: v{version})...")

    ctk_path = _get_customtkinter_path()
    sep = ";" if target_os == "windows" else ":"

    env = os.environ.copy()
    env["APP_VERSION_OVERRIDE"] = version
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    spec_file = Path("github-account-manager.spec")
    if spec_file.exists():
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "github-account-manager.spec",
        ]
    else:
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            "github-account-manager",
            "--windowed",
            "--add-data",
            f"{ctk_path}{sep}customtkinter",
            "--add-data",
            f"assets{sep}assets",
            "--icon",
            "assets/icon.ico",
            "--collect-all",
            "customtkinter",
            "--collect-all",
            "pydantic",
            "--hidden-import",
            "github_account_manager",
            "--hidden-import",
            "github_account_manager.platform.windows",
            "--hidden-import",
            "github_account_manager.platform.macos",
            "--hidden-import",
            "github_account_manager.platform.linux",
            "main.py",
        ]

    print("[BUILD] Running PyInstaller:", " ".join(cmd))
    res = subprocess.run(cmd, env=env)
    if res.returncode != 0:
        print("[ERROR] PyInstaller build failed!")
        sys.exit(res.returncode)

    print("[OK] PyInstaller build completed successfully.")


def create_release_archive(target_os: str) -> Path:
    dist_dir = Path("dist")

    if target_os == "windows":
        exe_file = dist_dir / "github-account-manager.exe"
        if not exe_file.exists():
            print(f"[ERROR] Output executable not found: {exe_file}")
            sys.exit(1)

        print(f"[PACKAGE] Compressing release archive for {target_os}...")
        archive_name = dist_dir / "github-account-manager-windows-x64.zip"
        with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(exe_file, arcname=exe_file.name)
        print(f"[OK] Created Windows Release: {archive_name}")
        return archive_name

    elif target_os == "macos":
        app_file = dist_dir / "github-account-manager.app"
        if not app_file.exists():
            app_file = dist_dir / "github-account-manager"
        archive_name = dist_dir / "github-account-manager-macos.zip"
        with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zf:
            if app_file.is_dir():
                for root, _, files in os.walk(app_file):
                    for file in files:
                        full_p = Path(root) / file
                        rel_p = full_p.relative_to(dist_dir)
                        zf.write(full_p, arcname=str(rel_p))
            else:
                zf.write(app_file, arcname=app_file.name)
        print(f"[OK] Created macOS Release: {archive_name}")
        return archive_name

    elif target_os == "linux":
        bin_file = dist_dir / "github-account-manager"
        if not bin_file.exists():
            print(f"[ERROR] Output binary not found: {bin_file}")
            sys.exit(1)
        try:
            os.chmod(bin_file, 0o755)
        except Exception:
            pass
        archive_name = dist_dir / "github-account-manager-linux-x64.tar.gz"
        with tarfile.open(archive_name, "w:gz") as tar:
            tar.add(bin_file, arcname="github-account-manager")
        print(f"[OK] Created Linux Release: {archive_name}")
        return archive_name

    return dist_dir


def publish_artifacts(target_os: str, archive_path: Path, publish_dir_str: Optional[str] = None):
    if publish_dir_str:
        pub_dir = Path(publish_dir_str)
    elif os.getenv("PUBLISH_DIR"):
        pub_dir = Path(os.getenv("PUBLISH_DIR"))
    else:
        pub_dir = Path(__file__).parent / "publish"

    print(f"[PUBLISH] Publishing build output to: {pub_dir}...")
    pub_dir.mkdir(parents=True, exist_ok=True)

    # Clean up old batch launcher or folders if present
    old_bat = pub_dir / "Launch-App.bat"
    if old_bat.exists():
        old_bat.unlink()
    old_folder = pub_dir / "github-account-manager"
    if old_folder.is_dir():
        shutil.rmtree(old_folder, ignore_errors=True)

    # Copy single standalone executable directly to Publish root
    dist_dir = Path("dist")
    if target_os == "windows":
        exe_file = dist_dir / "github-account-manager.exe"
        if exe_file.exists():
            dest_exe = pub_dir / "github-account-manager.exe"
            shutil.copy2(exe_file, dest_exe)
            print(f"[OK] Copied standalone executable directly to: {dest_exe}")
    elif target_os == "linux":
        bin_file = dist_dir / "github-account-manager"
        if bin_file.exists():
            dest_bin = pub_dir / "github-account-manager"
            shutil.copy2(bin_file, dest_bin)
            try:
                os.chmod(dest_bin, 0o755)
            except Exception:
                pass
            print(f"[OK] Copied standalone executable directly to: {dest_bin}")

    # Copy archive file
    if archive_path and archive_path.exists():
        dest_archive = pub_dir / archive_path.name
        shutil.copy2(archive_path, dest_archive)
        print(f"[OK] Copied release archive to: {dest_archive}")


def main():
    parser = argparse.ArgumentParser(description="Cross-platform build and packaging script.")
    parser.add_argument("--publish-dir", default=None, help="Directory to copy release artifacts to.")
    parser.add_argument("--version", default=None, help="Explicit version to set (e.g. 0.1.29).")
    args = parser.parse_args()

    target_os = get_target_platform()
    clean_build_artifacts()
    run_pyinstaller(target_os, version_override=args.version)
    archive = create_release_archive(target_os)
    publish_artifacts(target_os, archive, args.publish_dir)
    print("[SUCCESS] All build and release steps completed successfully!")


if __name__ == "__main__":
    main()