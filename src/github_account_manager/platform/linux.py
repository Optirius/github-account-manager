"""Linux-specific Platform Adapter implementation."""
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


class LinuxPlatformAdapter(PlatformAdapter):
    @property
    def os_name(self) -> str:
        return "linux"

    def get_ide_settings_paths(self, ide_id: str) -> List[Path]:
        config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

        ide_map = {
            "vscode": [
                config_dir / "Code" / "User" / "settings.json",
                config_dir / "Code - Insiders" / "User" / "settings.json",
            ],
            "cursor": [
                config_dir / "Cursor" / "User" / "settings.json",
            ],
            "windsurf": [
                config_dir / "Windsurf" / "User" / "settings.json",
            ],
            "vscodium": [
                config_dir / "VSCodium" / "User" / "settings.json",
            ],
        }
        return ide_map.get(ide_id.lower(), [])

    def detect_installed_apps(self) -> List[Dict[str, Any]]:
        known_definitions = [
            {
                "id": "code",
                "name": "Visual Studio Code",
                "category": "IDE / Editor",
                "icon": "💻",
                "binaries": ["code", "code-insiders"],
                "supports_isolation": True,
            },
            {
                "id": "cursor",
                "name": "Cursor AI Code Editor",
                "category": "IDE / Editor",
                "icon": "⚡",
                "binaries": ["cursor"],
                "supports_isolation": True,
            },
            {
                "id": "windsurf",
                "name": "Windsurf Editor",
                "category": "IDE / Editor",
                "icon": "🏄",
                "binaries": ["windsurf"],
                "supports_isolation": True,
            },
            {
                "id": "vscodium",
                "name": "VSCodium",
                "category": "IDE / Editor",
                "icon": "📦",
                "binaries": ["vscodium", "codium"],
                "supports_isolation": True,
            },
            {
                "id": "github-desktop",
                "name": "GitHub Desktop",
                "category": "Git GUI Client",
                "icon": "🐙",
                "binaries": ["github-desktop"],
                "supports_isolation": False,
            },
            {
                "id": "git",
                "name": "Git CLI",
                "category": "CLI / Engine",
                "icon": "🔧",
                "binaries": ["git"],
                "supports_isolation": False,
            },
        ]

        results = []
        for defn in known_definitions:
            installed = False
            exe_path = None

            for b in defn["binaries"]:
                p = shutil.which(b)
                if p:
                    installed = True
                    exe_path = p
                    break

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
        # Check ~/.git-credentials or secret-tool
        git_cred_file = Path.home() / ".git-credentials"
        if git_cred_file.exists():
            try:
                for line in git_cred_file.read_text(encoding="utf-8").splitlines():
                    if "github.com" in line:
                        credentials.append({
                            "target": "github.com (~/.git-credentials)",
                            "user": line.split("@")[0].split("//")[-1] if "@" in line else "Stored Credential",
                            "type": "Plaintext File Credential",
                            "is_conflicting": True,
                        })
            except Exception as e:
                logger.debug(f"Error reading .git-credentials: {e}")

        # Check secret-tool
        if shutil.which("secret-tool"):
            try:
                res = safe_subprocess_run(
                    ["secret-tool", "search", "service", "git"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res.returncode == 0 and "github.com" in res.stdout:
                    credentials.append({
                        "target": "github.com (libsecret)",
                        "user": "Secret Service Account",
                        "type": "Freedesktop Secret Item",
                        "is_conflicting": True,
                    })
            except Exception as e:
                logger.debug(f"secret-tool query notice: {e}")

        return credentials

    def delete_git_credential(self, target: str) -> bool:
        # If .git-credentials, clean github entries
        git_cred_file = Path.home() / ".git-credentials"
        if git_cred_file.exists():
            try:
                lines = [l for l in git_cred_file.read_text(encoding="utf-8").splitlines() if "github.com" not in l]
                git_cred_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to edit .git-credentials: {e}")

        # If secret-tool
        if shutil.which("secret-tool"):
            try:
                safe_subprocess_run(
                    ["secret-tool", "clear", "service", "git"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            except Exception as e:
                logger.debug(f"secret-tool clear notice: {e}")

        return True

    def get_default_ssh_dir(self) -> Path:
        return Path.home() / ".ssh"

    def get_default_gitconfig_path(self) -> Path:
        return Path.home() / ".gitconfig"

    def get_default_data_dir(self) -> Path:
        return Path.home() / ".github_account_manager"

    def get_system_font_family(self) -> str:
        return "Ubuntu"