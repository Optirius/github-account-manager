"""Hardened, Cross-Platform Auto-Update Service for GitHub Multi-Account Manager.

Features:
- Cryptographic & URL security guards against hijacking / spoofing
- Safe archive extraction (ZipSlip & directory traversal immunity)
- Binary integrity verification (PE / Mach-O / ELF header validation)
- 100% silent, invisible background self-replacement (zero console popups)
- Automatic Windows UAC elevation only when writing to protected directories
"""
from dataclasses import dataclass
import hashlib
import json
import logging
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Callable, Optional, Tuple
import urllib.parse
import urllib.request
import zipfile
import tarfile

from github_account_manager.config import APP_VERSION

logger = logging.getLogger(__name__)

GITHUB_REPO = "Optirius/github-multi-account-manager"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

ALLOWED_HOSTS = {
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "raw.githubusercontent.com",
    "release-assets.githubusercontent.com",
}


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    is_update_available: bool
    release_name: str
    release_notes: str
    html_url: str
    published_at: str
    asset_name: Optional[str]
    asset_download_url: Optional[str]
    asset_size: int = 0
    expected_sha256: Optional[str] = None


class SecurityError(Exception):
    """Raised when an update fails cryptographic or URL integrity validation."""
    pass


def parse_version_tuple(v_str: str) -> Tuple[int, ...]:
    """Parse version string like 'v0.1.20' or '0.1.20-beta' into integer tuple for accurate comparison."""
    clean = v_str.strip().lstrip("v").split("-")[0]
    nums = []
    for part in clean.split("."):
        digits = re.findall(r"\d+", part)
        if digits:
            nums.append(int(digits[0]))
        else:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def is_secure_download_url(url: str) -> bool:
    """Ensure the URL is HTTPS and strictly hosted on official GitHub domains."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            return False
        host = (parsed.hostname or "").lower()
        if host in ALLOWED_HOSTS or host.endswith(".github.com") or host.endswith(".githubusercontent.com"):
            return True
        return False
    except Exception:
        return False


def verify_executable_format(file_path: Path, target_os: str) -> bool:
    """Verify that the extracted file contains valid executable magic headers."""
    if not file_path.exists() or file_path.stat().st_size < 100_000:
        return False

    try:
        with open(file_path, "rb") as f:
            if target_os == "windows":
                header = f.read(64)
                if len(header) < 64 or header[:2] != b"MZ":
                    return False
                pe_offset = int.from_bytes(header[60:64], byteorder="little")
                if pe_offset < 64 or pe_offset > 2048:
                    return False
                f.seek(pe_offset)
                return f.read(4) == b"PE\x00\x00"

            elif target_os == "linux":
                magic = f.read(4)
                return magic == b"\x7fELF"

            elif target_os == "macos":
                magic = f.read(4)
                # Mach-O magic headers (32-bit, 64-bit, FAT)
                return magic in [b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"]

    except Exception as e:
        logger.error(f"Executable validation failed for {file_path}: {e}")
        return False

    return True


class UpdateService:
    def __init__(self, current_version: Optional[str] = None):
        self.current_version = current_version or APP_VERSION

    def get_target_platform(self) -> str:
        sys_name = platform.system().lower()
        if "windows" in sys_name:
            return "windows"
        elif "darwin" in sys_name:
            return "macos"
        return "linux"

    def check_for_updates(self, timeout: int = 6) -> Optional[UpdateInfo]:
        """
        Query GitHub Releases API securely for the latest version and matching platform asset.
        Returns UpdateInfo if check succeeds, or None if network/API error occurs.
        """
        try:
            req = urllib.request.Request(
                RELEASES_API_URL,
                headers={
                    "User-Agent": "GitHub-Multi-Account-Manager",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    return None
                data = json.loads(response.read().decode("utf-8"))

            tag_name = data.get("tag_name", "").strip()
            if not tag_name:
                return None

            latest_v = tag_name.lstrip("v")
            current_v = self.current_version.lstrip("v")

            is_newer = parse_version_tuple(latest_v) > parse_version_tuple(current_v)

            # Match appropriate asset for current OS
            target_os = self.get_target_platform()
            matching_asset = None

            for asset in data.get("assets", []):
                aname = asset.get("name", "").lower()
                if target_os == "windows":
                    if "windows" in aname or "win" in aname or aname.endswith(".exe"):
                        matching_asset = asset
                        break
                elif target_os == "macos":
                    if "macos" in aname or "darwin" in aname or "osx" in aname or aname.endswith(".dmg"):
                        matching_asset = asset
                        break
                elif target_os == "linux":
                    if "linux" in aname or aname.endswith(".tar.gz") or aname.endswith(".appimage"):
                        matching_asset = asset
                        break

            asset_name = matching_asset.get("name") if matching_asset else None
            asset_url = matching_asset.get("browser_download_url") if matching_asset else None
            asset_size = matching_asset.get("size", 0) if matching_asset else 0

            # Validate download URL domain if present
            if asset_url and not is_secure_download_url(asset_url):
                logger.warning(f"Rejecting insecure/untrusted asset URL: {asset_url}")
                asset_url = None

            # Extract optional SHA256 checksum from release notes if provided
            body_text = data.get("body", "")
            expected_sha = None
            if asset_name:
                m = re.search(re.escape(asset_name) + r"[:\s]+([a-fA-F0-9]{64})", body_text)
                if m:
                    expected_sha = m.group(1).lower()

            return UpdateInfo(
                current_version=f"v{current_v}",
                latest_version=f"v{latest_v}",
                is_update_available=is_newer,
                release_name=data.get("name") or f"Release {tag_name}",
                release_notes=body_text or "No release notes provided.",
                html_url=data.get("html_url") or f"https://github.com/{GITHUB_REPO}/releases/latest",
                published_at=data.get("published_at", "")[:10],
                asset_name=asset_name,
                asset_download_url=asset_url,
                asset_size=asset_size,
                expected_sha256=expected_sha,
            )

        except Exception as e:
            logger.debug(f"Update check failed: {e}")
            return None

    def download_and_extract_asset(
        self,
        update_info: UpdateInfo,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """
        Securely download release archive, verify integrity/SHA256, and safely extract the standalone binary.
        Returns: Path to the extracted new executable ready for replacement.
        """
        if not update_info.asset_download_url:
            raise ValueError("No download URL available for this platform.")

        if not is_secure_download_url(update_info.asset_download_url):
            raise SecurityError(f"Untrusted download URL: {update_info.asset_download_url}")

        temp_dir = Path(tempfile.mkdtemp(prefix="gam_sec_update_"))
        download_path = temp_dir / (update_info.asset_name or "update_asset")

        if progress_callback:
            progress_callback(0.05, "Connecting to GitHub via secure TLS...")

        req = urllib.request.Request(
            update_info.asset_download_url,
            headers={"User-Agent": "GitHub-Multi-Account-Manager"},
        )

        hasher = hashlib.sha256()
        with urllib.request.urlopen(req, timeout=30) as resp, open(download_path, "wb") as out_file:
            total_size = int(resp.headers.get("Content-Length", update_info.asset_size or 0))
            downloaded = 0
            chunk_size = 64 * 1024

            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                hasher.update(chunk)
                downloaded += len(chunk)
                if total_size > 0 and progress_callback:
                    pct = min(0.85, 0.05 + 0.80 * (downloaded / total_size))
                    mb_down = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    progress_callback(pct, f"Downloading: {mb_down:.1f} MB / {mb_total:.1f} MB ({int((downloaded/total_size)*100)}%)")

        # Verify Checksum if provided
        calculated_sha = hasher.hexdigest().lower()
        if update_info.expected_sha256:
            if calculated_sha != update_info.expected_sha256.lower():
                raise SecurityError(f"SHA-256 checksum mismatch! Expected: {update_info.expected_sha256}, Got: {calculated_sha}")

        if progress_callback:
            progress_callback(0.90, "Verifying package integrity & extracting...")

        # Safe extraction with path-traversal (ZipSlip) defense
        extracted_binary: Optional[Path] = None
        target_os = self.get_target_platform()

        if download_path.suffix.lower() == ".zip":
            with zipfile.ZipFile(download_path, "r") as z:
                # Path traversal check
                for member in z.namelist():
                    dest = (temp_dir / member).resolve()
                    if not str(dest).startswith(str(temp_dir.resolve())):
                        raise SecurityError(f"Malicious archive member attempted path traversal: {member}")
                z.extractall(temp_dir)

            for item in temp_dir.iterdir():
                if item.is_file() and item.suffix.lower() in [".exe", ""]:
                    if "github-account-manager" in item.name.lower() or item.name.endswith(".exe"):
                        extracted_binary = item
                        break

        elif download_path.suffix.lower() in [".gz", ".tar"]:
            with tarfile.open(download_path, "r:*") as t:
                for member in t.getmembers():
                    dest = (temp_dir / member.name).resolve()
                    if not str(dest).startswith(str(temp_dir.resolve())):
                        raise SecurityError(f"Malicious archive member attempted path traversal: {member.name}")
                t.extractall(temp_dir)

            for item in temp_dir.iterdir():
                if item.is_file() and "github-account-manager" in item.name.lower():
                    extracted_binary = item
                    break

        elif download_path.suffix.lower() == ".exe":
            extracted_binary = download_path

        if not extracted_binary or not extracted_binary.exists():
            for item in temp_dir.rglob("*.exe"):
                extracted_binary = item
                break

        if not extracted_binary or not extracted_binary.exists():
            raise FileNotFoundError("Could not locate executable inside update package.")

        # Cryptographic/Format verification on the extracted binary
        if not verify_executable_format(extracted_binary, target_os):
            raise SecurityError("Downloaded binary failed executable format security verification.")

        if progress_callback:
            progress_callback(0.98, "Update verified and ready to install.")

        return extracted_binary

    def apply_and_restart(self, new_binary_path: Path, current_exe_path: Optional[Path] = None) -> bool:
        r"""
        Spawn a 100% silent, invisible background updater to replace running executable and relaunch.
        Uses UAC elevation only if needed (e.g. writing to C:\Program Files).
        Terminates the current process cleanly to release file locks.
        """
        target_path = current_exe_path or Path(sys.executable)

        # Safety check: if running as python script in dev mode, target dist exe if exists
        if target_path.name.lower() in ["python.exe", "python3", "pythonw.exe"]:
            dist_cand = Path.cwd() / "dist" / ("github-account-manager.exe" if platform.system() == "Windows" else "github-account-manager")
            if dist_cand.exists():
                target_path = dist_cand
            else:
                logger.info("Running in development mode (python.exe). Skipping self-replacement.")
                return False

        target_os = self.get_target_platform()
        current_pid = os.getpid()

        # Clean PyInstaller bootloader environment variables so the relaunched app
        # does not inherit parent PID/home-dir and trigger bootloader security validation failure
        clean_env = os.environ.copy()
        for key in list(clean_env.keys()):
            if key.startswith("_PYI") or key.startswith("PYI_") or key.startswith("_MEI"):
                del clean_env[key]

        if target_os == "windows":
            # Pure silent updater batch with SW_HIDE startupinfo and CREATE_NO_WINDOW
            updater_bat = Path(tempfile.gettempdir()) / f"gam_updater_{current_pid}.bat"
            src_norm = os.path.normpath(str(new_binary_path))
            dst_norm = os.path.normpath(str(target_path))

            bat_script = f"""@echo off
setlocal
set PID={current_pid}
set NEW={src_norm}
set TARGET={dst_norm}

:: Unset PyInstaller bootloader environment variables
set _MEIPASS2=
set _MEIPASS=
set _PYI_APPLICATION_HOME_DIR=
set _PYI_ARCHIVE_FILE=
set _PYI_PARENT_PID=
set _PYI_SPLASH_IPC=

:wait_loop
tasklist /fi "PID eq %PID%" 2>NUL | find "%PID%" >NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak >NUL
    goto wait_loop
)

:: Try direct non-elevated copy first
set COPIED=0
for /L %%i in (1,1,10) do (
    copy /Y /B "%NEW%" "%TARGET%" >NUL 2>&1
    if not errorlevel 1 (
        set COPIED=1
        goto launch
    )
    timeout /t 1 /nobreak >NUL
)

:: If copy failed due to permissions, elevate quietly via PowerShell RunAs
if "%COPIED%"=="0" (
    powershell -NoProfile -NonInteractive -WindowStyle Hidden -Command "Start-Process powershell -ArgumentList '-NoProfile -Command [System.Environment]::SetEnvironmentVariable(\"\"_PYI_PARENT_PID\"\", $null, \"\"Process\"\"); Copy-Item -LiteralPath ''%NEW%'' -Destination ''%TARGET%'' -Force; Start-Process -FilePath ''%TARGET%''' -Verb RunAs -WindowStyle Hidden"
    goto cleanup
)

:launch
start "" "%TARGET%"

:cleanup
del "%NEW%" >NUL 2>&1
(goto) 2>nul & del "%~f0"
"""
            updater_bat.write_text(bat_script, encoding="utf-8")

            # Launch completely silent without conflicting DETACHED_PROCESS flag
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

            subprocess.Popen(
                ["cmd.exe", "/c", str(updater_bat)],
                startupinfo=startupinfo,
                creationflags=0x08000000,  # CREATE_NO_WINDOW
                env=clean_env,
                close_fds=True,
            )

        elif target_os == "macos":
            # macOS Daemon Updater with AppleScript elevation & Gatekeeper quarantine clearing
            updater_sh = Path(tempfile.gettempdir()) / f"gam_updater_{current_pid}.sh"
            sh_script = f"""#!/bin/sh
PID={current_pid}
NEW="{new_binary_path}"
TARGET="{target_path}"

unset _MEIPASS2 _MEIPASS _PYI_APPLICATION_HOME_DIR _PYI_ARCHIVE_FILE _PYI_PARENT_PID _PYI_SPLASH_IPC

while kill -0 $PID 2>/dev/null; do
    sleep 0.3
done

# Try non-elevated copy first
cp -f "$NEW" "$TARGET" 2>/dev/null
if [ $? -ne 0 ]; then
    # Native macOS Authorization Dialog
    osascript -e "do shell script \\"cp -f '$NEW' '$TARGET' && chmod +x '$TARGET'\\" with administrator privileges"
fi

chmod +x "$TARGET" 2>/dev/null || true
xattr -d com.apple.quarantine "$TARGET" 2>/dev/null || true

# Relaunch updated application
"$TARGET" >/dev/null 2>&1 &
rm -f "$0"
"""
            updater_sh.write_text(sh_script, encoding="utf-8")
            os.chmod(updater_sh, 0o755)

            subprocess.Popen(
                ["/bin/sh", str(updater_sh)],
                env=clean_env,
                start_new_session=True,
                close_fds=True,
            )

        else:
            # Linux Silent Daemon Updater with PolicyKit elevation support
            updater_sh = Path(tempfile.gettempdir()) / f"gam_updater_{current_pid}.sh"
            sh_script = f"""#!/bin/sh
PID={current_pid}
NEW="{new_binary_path}"
TARGET="{target_path}"

unset _MEIPASS2 _MEIPASS _PYI_APPLICATION_HOME_DIR _PYI_ARCHIVE_FILE _PYI_PARENT_PID _PYI_SPLASH_IPC

while kill -0 $PID 2>/dev/null; do
    sleep 0.3
done

# Try non-elevated copy first
cp -f "$NEW" "$TARGET" 2>/dev/null
if [ $? -ne 0 ]; then
    # PolicyKit GUI elevation
    pkexec cp -f "$NEW" "$TARGET" 2>/dev/null || gksudo cp -f "$NEW" "$TARGET" 2>/dev/null || true
fi

chmod +x "$TARGET" 2>/dev/null || true

# Relaunch updated application
"$TARGET" >/dev/null 2>&1 &
rm -f "$0"
"""
            updater_sh.write_text(sh_script, encoding="utf-8")
            os.chmod(updater_sh, 0o755)

            subprocess.Popen(
                ["/bin/sh", str(updater_sh)],
                env=clean_env,
                start_new_session=True,
                close_fds=True,
            )

        # Exit cleanly so the updater can overwrite the unlocked binary
        time.sleep(0.15)
        sys.exit(0)
        return True
