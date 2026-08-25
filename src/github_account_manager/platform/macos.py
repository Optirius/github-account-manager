"""macOS-specific Platform Adapter implementation."""
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional
import logging

from github_account_manager.platform.base import PlatformAdapter
from github_account_manager.utils import safe_subprocess_run

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
        """
        Dynamically discover installed IDEs, Git clients, and developer tools
        via macOS /Applications, ~/Applications, JetBrains paths, and PATH.
        """
        app_dirs = [
            Path("/Applications"),
            Path.home() / "Applications",
            Path.home() / "Applications" / "JetBrains Toolbox",
        ]

        discovered: Dict[str, Dict[str, Any]] = {}

        # 1. Primary Well-Known Definitions
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
                "id": "rider",
                "name": "JetBrains Rider",
                "category": "IDE / Editor",
                "icon": "🔴",
                "app_bundles": ["Rider.app", "JetBrains Rider.app"],
                "supports_isolation": True,
            },
            {
                "id": "idea",
                "name": "JetBrains IntelliJ IDEA",
                "category": "IDE / Editor",
                "icon": "💡",
                "app_bundles": ["IntelliJ IDEA.app", "IntelliJ IDEA CE.app"],
                "supports_isolation": True,
            },
            {
                "id": "pycharm",
                "name": "JetBrains PyCharm",
                "category": "IDE / Editor",
                "icon": "🐍",
                "app_bundles": ["PyCharm.app", "PyCharm CE.app"],
                "supports_isolation": True,
            },
            {
                "id": "visual_studio",
                "name": "Visual Studio for Mac",
                "category": "IDE / Editor",
                "icon": "🟣",
                "app_bundles": ["Visual Studio.app"],
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
                "id": "gitkraken",
                "name": "GitKraken",
                "category": "Git GUI Client",
                "icon": "🐙",
                "app_bundles": ["GitKraken.app"],
                "supports_isolation": False,
            },
            {
                "id": "sourcetree",
                "name": "Sourcetree",
                "category": "Git GUI Client",
                "icon": "🌳",
                "app_bundles": ["Sourcetree.app"],
                "supports_isolation": False,
            },
            {
                "id": "sublime_merge",
                "name": "Sublime Merge",
                "category": "Git GUI Client",
                "icon": "📑",
                "app_bundles": ["Sublime Merge.app"],
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

        for defn in known_definitions:
            installed = False
            exe_path = None

            for app_dir in app_dirs:
                if not app_dir.exists():
                    continue
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
                discovered[defn["id"]] = {
                    "id": defn["id"],
                    "name": defn["name"],
                    "category": defn["category"],
                    "icon": defn["icon"],
                    "exe_path": exe_path,
                    "supports_isolation": defn["supports_isolation"],
                }

        # 2. Dynamic Bundle Scanner (Discovers all developer .app bundles)
        keywords = ["git", "github", "studio", "rider", "intellij", "pycharm", "webstorm", "clion", "goland", "rustrover", "code", "cursor", "windsurf", "eclipse", "sublime", "sourcetree", "kraken", "xcode", "fleet", "positron"]
        for app_dir in app_dirs:
            if app_dir.exists():
                try:
                    for app_bundle in app_dir.glob("*.app"):
                        bundle_name = app_bundle.stem
                        name_l = bundle_name.lower()
                        if any(k in name_l for k in keywords):
                            app_id = re.sub(r"[^a-zA-Z0-9_]", "_", bundle_name.lower()).strip("_")
                            if not any(d["name"].lower() == bundle_name.lower() for d in discovered.values()):
                                is_git_gui = any(g in name_l for g in ["git", "github", "kraken", "sourcetree", "merge"])
                                discovered[app_id] = {
                                    "id": app_id,
                                    "name": bundle_name,
                                    "category": "Git GUI Client" if is_git_gui else "IDE / Editor",
                                    "icon": "🐙" if is_git_gui else "💻",
                                    "exe_path": str(app_bundle),
                                    "supports_isolation": "code" in name_l or "cursor" in name_l or "windsurf" in name_l,
                                }
                except Exception:
                    pass

        return list(discovered.values())

    def get_ide_github_accounts(self) -> List[Dict[str, Any]]:
        """Extract GitHub accounts configured inside JetBrains IDE options on macOS."""
        accounts: List[Dict[str, Any]] = []
        jetbrains_dir = Path.home() / "Library" / "Application Support" / "JetBrains"
        if jetbrains_dir.exists():
            for xml_file in jetbrains_dir.glob("*/options/github.xml"):
                try:
                    ide_name = xml_file.parent.parent.name
                    content = xml_file.read_text(encoding="utf-8", errors="ignore")
                    for match in re.finditer(r'<account\s+[^>]*name="([^"]+)"', content):
                        acc_name = match.group(1)
                        server_m = re.search(r'<server\s+[^>]*host="([^"]+)"', content)
                        server = server_m.group(1) if server_m else "github.com"
                        accounts.append({
                            "ide": ide_name,
                            "account": acc_name,
                            "server": server,
                            "source": f"JetBrains ({ide_name})",
                        })
                except Exception:
                    pass
        return accounts

    def list_git_credentials(self) -> List[Dict[str, Any]]:
        credentials = []
        try:
            res = safe_subprocess_run(
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
            res = safe_subprocess_run(
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