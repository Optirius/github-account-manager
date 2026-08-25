"""Universal Cross-Platform Build & Packaging Script for Windows, macOS, and Linux."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile

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
    print("🧹 Cleaning previous build artifacts...")
    for folder in ["build", "dist"]:
        p = Path(folder)
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


def run_pyinstaller(target_os: str):
    print(f"📦 Packaging for {target_os.upper()}...")

    ctk_path = Path(customtkinter.__file__).parent
    sep = ";" if target_os == "windows" else ":"

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

    print("Running PyInstaller:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("❌ PyInstaller build failed!")
        sys.exit(res.returncode)

    print("✓ PyInstaller build completed successfully.")


def create_release_archive(target_os: str):
    dist_dir = Path("dist")
    app_dir = dist_dir / "github-account-manager"

    if not app_dir.exists():
        print(f"❌ Output directory not found: {app_dir}")
        sys.exit(1)

    print(f"🗜️ Compressing release archive for {target_os}...")

    if target_os == "windows":
        archive_name = dist_dir / "github-account-manager-windows-x64.zip"
        with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(app_dir):
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(dist_dir)
                    zf.write(full_p, arcname=str(rel_p))
        print(f"✓ Created Windows Release: {archive_name}")

    elif target_os == "macos":
        archive_name = dist_dir / "github-account-manager-macos.zip"
        with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(app_dir):
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(dist_dir)
                    zf.write(full_p, arcname=str(rel_p))
        print(f"✓ Created macOS Release: {archive_name}")

    elif target_os == "linux":
        archive_name = dist_dir / "github-account-manager-linux-x64.tar.gz"
        with tarfile.open(archive_name, "w:gz") as tar:
            tar.add(app_dir, arcname="github-account-manager")
        print(f"✓ Created Linux Release: {archive_name}")


def main():
    target_os = get_target_platform()
    clean_build_artifacts()
    run_pyinstaller(target_os)
    create_release_archive(target_os)
    print("🎉 All packaging steps completed successfully!")


if __name__ == "__main__":
    main()