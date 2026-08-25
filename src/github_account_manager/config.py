"""Application configuration and constants."""
from pathlib import Path
import os

APP_NAME = "GitHub Multi-Account Manager"
APP_ID = "com.optirius.github_account_manager"
APP_VERSION = "0.1.0"

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
