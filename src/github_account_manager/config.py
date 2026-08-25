"""Application configuration and constants."""
from pathlib import Path
import os

APP_NAME = "GitHub Multi-Account Manager"
APP_ID = "com.optirius.github_account_manager"


def _resolve_app_version() -> str:
    env_ver = os.getenv("APP_VERSION_OVERRIDE")
    if env_ver:
        return env_ver.strip().lstrip("v")

    try:
        import subprocess
        res = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0 and res.stdout.strip().isdigit():
            return f"0.1.{res.stdout.strip()}"
    except Exception:
        pass

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

# GitHub endpoints
GITHUB_API_BASE = "https://api.github.com"
