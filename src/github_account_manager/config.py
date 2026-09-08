"""Application configuration and constants."""
from pathlib import Path
import os

APP_NAME = "GitHub Multi-Account Manager"
APP_ID = "com.optirius.github_account_manager"


from github_account_manager.version import get_version

APP_VERSION = get_version()

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
