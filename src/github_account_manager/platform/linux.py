"""Linux-specific Platform Adapter implementation."""
import os
from pathlib import Path
import re
import shutil
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
        """
        Dynamically discover installed IDEs, Git clients, and developer tools
        via XDG .desktop files, JetBrains directories, Flatpak/Snap, and PATH.
        """
        discovered: Dict[str, Dict[str, Any]] = {}

        # 1. Primary Well-Known Definitions
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
                "id": "rider",
                "name": "JetBrains Rider",
                "category": "IDE / Editor",
                "icon": "🔴",
                "binaries": ["rider", "rider.sh"],
                "supports_isolation": True,
            },
            {
                "id": "idea",
                "name": "JetBrains IntelliJ IDEA",
                "category": "IDE / Editor",
                "icon": "💡",
                "binaries": ["idea", "idea.sh", "intellij-idea-ultimate-edition", "intellij-idea-community-edition"],
                "supports_isolation": True,
            },
            {
                "id": "pycharm",
                "name": "JetBrains PyCharm",
                "category": "IDE / Editor",
                "icon": "🐍",
                "binaries": ["pycharm", "pycharm.sh", "pycharm-community", "pycharm-professional"],
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
                "id": "gitkraken",
                "name": "GitKraken",
                "category": "Git GUI Client",
                "icon": "🐙",
                "binaries": ["gitkraken"],
                "supports_isolation": False,
            },
            {
                "id": "sublime_merge",
                "name": "Sublime Merge",
                "category": "Git GUI Client",
                "icon": "📑",
                "binaries": ["sublime_merge", "smerge"],
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
                discovered[defn["id"]] = {
                    "id": defn["id"],
                    "name": defn["name"],
                    "category": defn["category"],
                    "icon": defn["icon"],
                    "exe_path": exe_path,
                    "supports_isolation": defn["supports_isolation"],
                }

        # 2. Dynamic XDG .desktop file scanner (Discovers any desktop-installed IDEs/Git clients)
        desktop_dirs = [
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
            Path.home() / ".local" / "share" / "applications",
            Path("/var/lib/flatpak/exports/share/applications"),
            Path("/var/lib/snapd/desktop/applications"),
        ]
        keywords = ["git", "github", "studio", "rider", "intellij", "pycharm", "webstorm", "clion", "goland", "rustrover", "code", "cursor", "windsurf", "eclipse", "sublime", "sourcetree", "kraken", "fleet", "positron"]
        
        for d_dir in desktop_dirs:
            if d_dir.exists():
                try:
                    for d_file in d_dir.glob("*.desktop"):
                        try:
                            content = d_file.read_text(encoding="utf-8", errors="ignore")
                            name_m = re.search(r"^Name=(.+)$", content, re.MULTILINE)
                            exec_m = re.search(r"^Exec=(.+)$", content, re.MULTILINE)
                            cats_m = re.search(r"^Categories=(.+)$", content, re.MULTILINE)

                            if name_m:
                                name = name_m.group(1).strip()
                                name_l = name.lower()
                                exec_cmd = exec_m.group(1).split()[0].strip('"') if exec_m else str(d_file)
                                is_dev = cats_m and ("Development" in cats_m.group(1) or "IDE" in cats_m.group(1))

                                if (is_dev and any(k in name_l for k in keywords)) or any(k in name_l for k in keywords):
                                    app_id = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower()).strip("_")
                                    if not any(d["name"].lower() == name.lower() for d in discovered.values()):
                                        is_git_gui = any(g in name_l for g in ["git", "github", "kraken", "sourcetree", "merge"])
                                        discovered[app_id] = {
                                            "id": app_id,
                                            "name": name,
                                            "category": "Git GUI Client" if is_git_gui else "IDE / Editor",
                                            "icon": "🐙" if is_git_gui else "💻",
                                            "exe_path": exec_cmd,
                                            "supports_isolation": "code" in name_l or "cursor" in name_l or "windsurf" in name_l,
                                        }
                        except Exception:
                            pass
                except Exception:
                    pass

        return list(discovered.values())

    def get_ide_github_accounts(self) -> List[Dict[str, Any]]:
        """Extract GitHub accounts configured inside JetBrains IDE options on Linux."""
        accounts: List[Dict[str, Any]] = []
        jetbrains_dir = Path.home() / ".config" / "JetBrains"
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