"""Application configuration and constants."""
from pathlib import Path
import os

APP_NAME = "GitHub Multi-Account Manager"
APP_ID = "com.optirius.github_account_manager"


def _resolve_app_version() -> str:
    # 1. Runtime environment variable override (if explicitly supplied)
    env_ver = os.getenv("APP_VERSION_OVERRIDE")
    if env_ver:
        return env_ver.strip().lstrip("v")

    # 2. Build-time baked _version.py (populated during PyInstaller build)
    try:
        from github_account_manager._version import __version__
        if __version__ and __version__ != "0.1.0":
            return __version__.strip().lstrip("v")
    except ImportError:
        pass

    # 3. Check for bundled version.txt (in PyInstaller sys._MEIPASS or assets)
    try:
        import sys
        base_dirs = [
            Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent)),
            Path(__file__).resolve().parent.parent.parent,
        ]
        for base in base_dirs:
            for candidate in [base / "version.txt", base / "assets" / "version.txt", base / "github_account_manager" / "version.txt"]:
                if candidate.exists():
                    val = candidate.read_text(encoding="utf-8").strip().lstrip("v")
                    if val and val != "0.1.0":
                        return val
    except Exception:
        pass

    # 4. Live git commit count (during active local development)
    try:
        import subprocess
        import sys
        kw = {"creationflags": 0x08000000} if sys.platform == "win32" else {}
        res = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            **kw,
        )
        if res.returncode == 0 and res.stdout.strip().isdigit():
            return f"0.1.{res.stdout.strip()}"
    except Exception:
        pass

    # 5. Default fallback
    return "0.1.0"


APP_VERSION = _resolve_app_version()

# Directories and paths
DATA_DIR = Path.home() / ".github_account_manager"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = DATA_DIR / "config.json"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SSH_DIR = Path.home() / ".ssh"
DEFAULT_SSH_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_GITCONFIG = Path.home() / ".gitconfig"


def _resolve_assets_dir() -> Path:
    import sys
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parent.parent.parent / "assets"


ASSETS_DIR = _resolve_assets_dir()

# GitHub endpoints
GITHUB_API_BASE = "https://api.github.com"
