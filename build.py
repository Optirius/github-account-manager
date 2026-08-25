"""Universal Cross-Platform Build & Packaging Script for Windows, macOS, and Linux."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile

# Ensure stdout/stderr handles UTF-8 safely without crashing on CP1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import customtkinter


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


def resolve_version() -> str:
    env_ver = os.getenv("APP_VERSION_OVERRIDE")
    if env_ver:
        return env_ver.strip().lstrip("v")
    try:
        res = subprocess.run(["git", "rev-list", "--count", "HEAD"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip().isdigit():
            return f"0.1.{res.stdout.strip()}"
    except Exception:
        pass
    return "0.1.0"


def run_pyinstaller(target_os: str):
    version = resolve_version()
    print(f"[BUILD] Packaging for {target_os.upper()} (Version: v{version})...")

    ctk_path = Path(customtkinter.__file__).parent
    sep = ";" if target_os == "windows" else ":"

    env = os.environ.copy()
    env["APP_VERSION_OVERRIDE"] = version
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "github-account-manager",
        "--windowed",
        "--add-data",
        f"{ctk_path}{sep}customtkinter",
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


def create_release_archive(target_os: str):
    dist_dir = Path("dist")
    app_dir = dist_dir / "github-account-manager"

    if not app_dir.exists():
        print(f"[ERROR] Output directory not found: {app_dir}")
        sys.exit(1)

    print(f"[PACKAGE] Compressing release archive for {target_os}...")

    if target_os == "windows":
        archive_name = dist_dir / "github-account-manager-windows-x64.zip"
        with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(app_dir):
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(dist_dir)
                    zf.write(full_p, arcname=str(rel_p))
        print(f"[OK] Created Windows Release: {archive_name}")

    elif target_os == "macos":
        archive_name = dist_dir / "github-account-manager-macos.zip"
        with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(app_dir):
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(dist_dir)
                    zf.write(full_p, arcname=str(rel_p))
        print(f"[OK] Created macOS Release: {archive_name}")

    elif target_os == "linux":
        archive_name = dist_dir / "github-account-manager-linux-x64.tar.gz"
        with tarfile.open(archive_name, "w:gz") as tar:
            tar.add(app_dir, arcname="github-account-manager")
        print(f"[OK] Created Linux Release: {archive_name}")


def main():
    target_os = get_target_platform()
    clean_build_artifacts()
    run_pyinstaller(target_os)
    create_release_archive(target_os)
    print("[SUCCESS] All packaging steps completed successfully!")


if __name__ == "__main__":
    main()