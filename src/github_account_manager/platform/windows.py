"""Windows-specific Platform Adapter implementation."""
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional
import logging

try:
    import winreg
except ImportError:
    winreg = None

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
        """
        Dynamically discover installed IDEs, Git GUI clients, and developer tools
        via the Windows Registry, JetBrains directories, AppData, and system paths.
        """
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        appdata = os.environ.get("APPDATA", "")

        discovered: Dict[str, Dict[str, Any]] = {}

        # 1. Primary Well-Known Definitions
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
                "id": "visual_studio",
                "name": "Microsoft Visual Studio",
                "category": "IDE / Editor",
                "icon": "🟣",
                "exe_candidates": (
                    list(Path(prog_files).glob("Microsoft Visual Studio/**/devenv.exe"))
                    + list(Path(prog_files_x86).glob("Microsoft Visual Studio/**/devenv.exe"))
                ),
                "supports_isolation": True,
            },
            {
                "id": "rider",
                "name": "JetBrains Rider",
                "category": "IDE / Editor",
                "icon": "🔴",
                "exe_candidates": (
                    list(Path(local_appdata).glob("Programs/**/rider*.exe"))
                    + list(Path(prog_files).glob("JetBrains/**/rider*.exe"))
                    + list(Path(local_appdata).glob("JetBrains/Toolbox/apps/**/rider*.exe"))
                ),
                "supports_isolation": True,
            },
            {
                "id": "idea",
                "name": "JetBrains IntelliJ IDEA",
                "category": "IDE / Editor",
                "icon": "💡",
                "exe_candidates": (
                    list(Path(local_appdata).glob("Programs/**/idea*.exe"))
                    + list(Path(prog_files).glob("JetBrains/**/idea*.exe"))
                    + list(Path(local_appdata).glob("JetBrains/Toolbox/apps/**/idea*.exe"))
                ),
                "supports_isolation": True,
            },
            {
                "id": "pycharm",
                "name": "JetBrains PyCharm",
                "category": "IDE / Editor",
                "icon": "🐍",
                "exe_candidates": (
                    list(Path(local_appdata).glob("Programs/**/pycharm*.exe"))
                    + list(Path(prog_files).glob("JetBrains/**/pycharm*.exe"))
                    + list(Path(local_appdata).glob("JetBrains/Toolbox/apps/**/pycharm*.exe"))
                ),
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
                "id": "gitkraken",
                "name": "GitKraken",
                "category": "Git GUI Client",
                "icon": "🐙",
                "exe_candidates": list(Path(local_appdata).glob("gitkraken/**/gitkraken.exe")),
                "supports_isolation": False,
            },
            {
                "id": "sourcetree",
                "name": "SourceTree",
                "category": "Git GUI Client",
                "icon": "🌳",
                "exe_candidates": [
                    Path(local_appdata) / "SourceTree" / "SourceTree.exe",
                    Path(prog_files) / "Atlassian" / "SourceTree" / "SourceTree.exe",
                ],
                "supports_isolation": False,
            },
            {
                "id": "sublime_merge",
                "name": "Sublime Merge",
                "category": "Git GUI Client",
                "icon": "📑",
                "exe_candidates": [
                    Path(prog_files) / "Sublime Merge" / "sublime_merge.exe",
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

        for defn in known_definitions:
            for cand in defn["exe_candidates"]:
                if cand.exists():
                    discovered[defn["id"]] = {
                        "id": defn["id"],
                        "name": defn["name"],
                        "category": defn["category"],
                        "icon": defn["icon"],
                        "exe_path": str(cand),
                        "supports_isolation": defn["supports_isolation"],
                    }
                    break
            if defn["id"] not in discovered and shutil.which(defn["id"]):
                discovered[defn["id"]] = {
                    "id": defn["id"],
                    "name": defn["name"],
                    "category": defn["category"],
                    "icon": defn["icon"],
                    "exe_path": shutil.which(defn["id"]),
                    "supports_isolation": defn["supports_isolation"],
                }

        # 2. Dynamic Registry Scanner (Discovers all installed development apps)
        if winreg is not None:
            reg_keys = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]
            keywords = ["git", "github", "visual studio", "rider", "intellij", "pycharm", "webstorm", "clion", "goland", "rustrover", "code", "cursor", "windsurf", "eclipse", "sublime merge", "sourcetree", "gitkraken", "vscodium", "fleet", "positron"]
            ignore = ["pack", "sdk", "runtime", "diagnostic", "wmi", "setup", "helper", "intellisense", "toolset", "coveragemsi", "fonts", "logitech", "protocolhandler", "installer"]

            for root_h, subkey in reg_keys:
                try:
                    with winreg.OpenKey(root_h, subkey) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                sub_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, sub_name) as app_key:
                                    name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                                    name_l = name.lower()
                                    if any(k in name_l for k in keywords) and not any(ign in name_l for ign in ignore):
                                        loc = ""
                                        try:
                                            loc, _ = winreg.QueryValueEx(app_key, "InstallLocation")
                                        except Exception:
                                            pass
                                        if not loc:
                                            try:
                                                icon_val, _ = winreg.QueryValueEx(app_key, "DisplayIcon")
                                                loc = icon_val.split(",")[0].strip('"')
                                            except Exception:
                                                pass
                                        app_id = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower()).strip("_")
                                        if not any(d["name"].lower() == name.lower() for d in discovered.values()):
                                            is_git_gui = any(g in name_l for g in ["git", "github", "kraken", "sourcetree", "merge"])
                                            discovered[app_id] = {
                                                "id": app_id,
                                                "name": name,
                                                "category": "Git GUI Client" if is_git_gui else "IDE / Editor",
                                                "icon": "🐙" if is_git_gui else "💻",
                                                "exe_path": loc or "System Path",
                                                "supports_isolation": "code" in name_l or "cursor" in name_l or "windsurf" in name_l,
                                            }
                            except Exception:
                                pass
                except Exception:
                    pass

        # 3. Dynamic JetBrains Directory Scanner
        jetbrains_roots = [
            Path(appdata) / "JetBrains",
            Path(local_appdata) / "JetBrains" / "Toolbox" / "apps",
            Path(prog_files) / "JetBrains",
        ]
        for jb_root in jetbrains_roots:
            if jb_root.exists():
                for folder in jb_root.glob("*"):
                    if folder.is_dir() and not folder.name.startswith("."):
                        clean_name = re.sub(r"[0-9\.\-_]+$", "", folder.name).strip()
                        if clean_name:
                            app_id = f"jetbrains_{clean_name.lower()}"
                            if app_id not in discovered and not any(clean_name.lower() in d["name"].lower() for d in discovered.values()):
                                discovered[app_id] = {
                                    "id": app_id,
                                    "name": f"JetBrains {clean_name.capitalize()}",
                                    "category": "IDE / Editor",
                                    "icon": "🔴" if "rider" in clean_name.lower() else "💡",
                                    "exe_path": str(folder),
                                    "supports_isolation": True,
                                }

        return list(discovered.values())

    def get_ide_github_accounts(self) -> List[Dict[str, Any]]:
        """Extract GitHub accounts configured inside external IDEs (such as JetBrains Rider / IntelliJ / PyCharm)."""
        accounts: List[Dict[str, Any]] = []
        appdata = os.environ.get("APPDATA", "")
        jetbrains_dir = Path(appdata) / "JetBrains"
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