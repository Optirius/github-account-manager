"""macOS-specific Platform Adapter implementation."""
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional
import logging

from github_account_manager.platform.base import PlatformAdapter

logger = logging.getLogger(__name__)


class MacOSPlatformAdapter(PlatformAdapter):
    @property
    def os_name(self) -> str:
        return "macos"

    def get_ide_settings_paths(self, ide_id: str) -> List[Path]:
        app_support = Path.home() / "Library" / "Application Support"

        ide_map = {
            "vscode": [
                app_support / "Code" / "User" / "settings.json",
                app_support / "Code - Insiders" / "User" / "settings.json",
            ],
            "cursor": [
                app_support / "Cursor" / "User" / "settings.json",
            ],
            "windsurf": [
                app_support / "Windsurf" / "User" / "settings.json",
            ],
            "vscodium": [
                app_support / "VSCodium" / "User" / "settings.json",
            ],
        }
        return ide_map.get(ide_id.lower(), [])

    def detect_installed_apps(self) -> List[Dict[str, Any]]:
        app_dirs = [
            Path("/Applications"),
            Path.home() / "Applications",
        ]

        known_definitions = [
            {
                "id": "vscode",
                "name": "Visual Studio Code",
                "category": "IDE / Editor",
                "icon": "💻",
                "app_bundles": ["Visual Studio Code.app", "Visual Studio Code - Insiders.app"],
                "supports_isolation": True,
            },
            {
                "id": "cursor",
                "name": "Cursor AI Code Editor",
                "category": "IDE / Editor",
                "icon": "⚡",
                "app_bundles": ["Cursor.app"],
                "supports_isolation": True,
            },
            {
                "id": "windsurf",
                "name": "Windsurf Editor",
                "category": "IDE / Editor",
                "icon": "🏄",
                "app_bundles": ["Windsurf.app"],
                "supports_isolation": True,
            },
            {
                "id": "vscodium",
                "name": "VSCodium",
                "category": "IDE / Editor",
                "icon": "📦",
                "app_bundles": ["VSCodium.app"],
                "supports_isolation": True,
            },
            {
                "id": "github_desktop",
                "name": "GitHub Desktop",
                "category": "Git GUI Client",
                "icon": "🐙",
                "app_bundles": ["GitHub Desktop.app"],
                "supports_isolation": False,
            },
            {
                "id": "git_cli",
                "name": "Git (Homebrew / Xcode)",
                "category": "CLI / Engine",
                "icon": "🔧",
                "app_bundles": [],
                "supports_isolation": False,
            },
        ]

        results = []
        for defn in known_definitions:
            installed = False
            exe_path = None

            for app_dir in app_dirs:
                for bundle in defn["app_bundles"]:
                    cand = app_dir / bundle
                    if cand.exists():
                        installed = True
                        exe_path = str(cand)
                        break
                if installed:
                    break

            if not installed and shutil.which(defn["id"]):
                installed = True
                exe_path = shutil.which(defn["id"])
            elif not installed and defn["id"] == "git_cli" and (shutil.which("git") or Path("/usr/bin/git").exists()):
                installed = True
                exe_path = shutil.which("git") or "/usr/bin/git"

            if installed:
                results.append({
                    "id": defn["id"],
                    "name": defn["name"],
                    "category": defn["category"],
                    "icon": defn["icon"],
                    "exe_path": exe_path,
                    "supports_isolation": defn["supports_isolation"],
                })

        return results

    def list_git_credentials(self) -> List[Dict[str, Any]]:
        credentials = []
        try:
            res = subprocess.run(
                ["security", "find-internet-password", "-s", "github.com"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                user_m = re.search(r'"acct"<blob>="([^"]+)"', res.stdout)
                user = user_m.group(1) if user_m else "macOS Keychain Account"
                credentials.append({
                    "target": "github.com (macOS Keychain)",
                    "user": user,
                    "type": "macOS Keychain Item",
                    "is_conflicting": True,
                })
        except Exception as e:
            logger.debug(f"macOS security lookup notice: {e}")

        return credentials

    def delete_git_credential(self, target: str) -> bool:
        try:
            res = subprocess.run(
                ["security", "delete-internet-password", "-s", "github.com"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to delete macOS Keychain credential '{target}': {e}")
            return False

    def get_default_ssh_dir(self) -> Path:
        return Path.home() / ".ssh"

    def get_default_gitconfig_path(self) -> Path:
        return Path.home() / ".gitconfig"

    def get_default_data_dir(self) -> Path:
        return Path.home() / ".github_account_manager"

    def get_system_font_family(self) -> str:
        return ".SF NS Text"