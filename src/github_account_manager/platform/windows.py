"""Windows-specific Platform Adapter implementation."""
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional
import logging

from github_account_manager.platform.base import PlatformAdapter
from github_account_manager.utils import safe_subprocess_run

logger = logging.getLogger(__name__)


class WindowsPlatformAdapter(PlatformAdapter):
    @property
    def os_name(self) -> str:
        return "windows"

    def get_ide_settings_paths(self, ide_id: str) -> List[Path]:
        appdata = os.environ.get("APPDATA")
        appdata_path = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"

        ide_map = {
            "vscode": [
                appdata_path / "Code" / "User" / "settings.json",
                appdata_path / "Code - Insiders" / "User" / "settings.json",
            ],
            "cursor": [
                appdata_path / "Cursor" / "User" / "settings.json",
            ],
            "windsurf": [
                appdata_path / "Windsurf" / "User" / "settings.json",
            ],
            "vscodium": [
                appdata_path / "VSCodium" / "User" / "settings.json",
            ],
        }
        return ide_map.get(ide_id.lower(), [])

    def detect_installed_apps(self) -> List[Dict[str, Any]]:
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")

        known_definitions = [
            {
                "id": "vscode",
                "name": "Visual Studio Code",
                "category": "IDE / Editor",
                "icon": "💻",
                "exe_candidates": [
                    Path(local_appdata) / "Programs" / "Microsoft VS Code" / "Code.exe",
                    Path(prog_files) / "Microsoft VS Code" / "Code.exe",
                ],
                "supports_isolation": True,
            },
            {
                "id": "cursor",
                "name": "Cursor AI Code Editor",
                "category": "IDE / Editor",
                "icon": "⚡",
                "exe_candidates": [
                    Path(local_appdata) / "Programs" / "cursor" / "Cursor.exe",
                    Path(prog_files) / "Cursor" / "Cursor.exe",
                ],
                "supports_isolation": True,
            },
            {
                "id": "windsurf",
                "name": "Windsurf Editor",
                "category": "IDE / Editor",
                "icon": "🏄",
                "exe_candidates": [
                    Path(local_appdata) / "Programs" / "Windsurf" / "Windsurf.exe",
                    Path(prog_files) / "Windsurf" / "Windsurf.exe",
                ],
                "supports_isolation": True,
            },
            {
                "id": "vscodium",
                "name": "VSCodium",
                "category": "IDE / Editor",
                "icon": "📦",
                "exe_candidates": [
                    Path(local_appdata) / "Programs" / "VSCodium" / "VSCodium.exe",
                    Path(prog_files) / "VSCodium" / "VSCodium.exe",
                ],
                "supports_isolation": True,
            },
            {
                "id": "github_desktop",
                "name": "GitHub Desktop",
                "category": "Git GUI Client",
                "icon": "🐙",
                "exe_candidates": [
                    Path(local_appdata) / "GitHubDesktop" / "GitHubDesktop.exe",
                ],
                "supports_isolation": False,
            },
            {
                "id": "git_windows",
                "name": "Git for Windows",
                "category": "CLI / Engine",
                "icon": "🔧",
                "exe_candidates": [
                    Path(prog_files) / "Git" / "cmd" / "git.exe",
                    Path(prog_files_x86) / "Git" / "cmd" / "git.exe",
                ],
                "supports_isolation": False,
            },
        ]

        results = []
        for defn in known_definitions:
            installed = False
            exe_path = None

            for cand in defn["exe_candidates"]:
                if cand.exists():
                    installed = True
                    exe_path = str(cand)
                    break

            if not installed and shutil.which(defn["id"]):
                installed = True
                exe_path = shutil.which(defn["id"])

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
            res = safe_subprocess_run(["cmdkey", "/list"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                raw_entries = res.stdout.split("----------------------------------")
                for entry in raw_entries:
                    if "git" in entry.lower() or "github" in entry.lower():
                        target_m = re.search(r"Target:\s*(.+)", entry, re.IGNORECASE)
                        user_m = re.search(r"User:\s*(.+)", entry, re.IGNORECASE)
                        type_m = re.search(r"Type:\s*(.+)", entry, re.IGNORECASE)

                        target = target_m.group(1).strip() if target_m else "Unknown"
                        user = user_m.group(1).strip() if user_m else "None"
                        ctype = type_m.group(1).strip() if type_m else "Generic"

                        credentials.append({
                            "target": target,
                            "user": user,
                            "type": ctype,
                            "is_conflicting": "github.com" in target.lower(),
                        })
        except Exception as e:
            logger.error(f"Error listing Windows credentials: {e}")

        return credentials

    def delete_git_credential(self, target: str) -> bool:
        try:
            res = safe_subprocess_run(["cmdkey", f"/delete:{target}"], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to delete Windows credential '{target}': {e}")
            return False

    def get_default_ssh_dir(self) -> Path:
        return Path.home() / ".ssh"

    def get_default_gitconfig_path(self) -> Path:
        return Path.home() / ".gitconfig"

    def get_default_data_dir(self) -> Path:
        return Path.home() / ".github_account_manager"

    def get_system_font_family(self) -> str:
        return "Segoe UI"