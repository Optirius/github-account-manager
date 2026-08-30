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


def _find_visual_studio_exes(prog_files: str, prog_files_x86: str) -> List[Path]:
    """Fast, shallow check for Visual Studio devenv.exe without unbounded recursive globs."""
    exes = []
    for base_dir in [Path(prog_files) / "Microsoft Visual Studio", Path(prog_files_x86) / "Microsoft Visual Studio"]:
        if base_dir.exists():
            try:
                for year in base_dir.iterdir():
                    if year.is_dir():
                        try:
                            for edition in year.iterdir():
                                if edition.is_dir():
                                    cand = edition / "Common7" / "IDE" / "devenv.exe"
                                    if cand.exists():
                                        exes.append(cand)
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError):
                pass
    return exes


def _find_jetbrains_exes(prog_files: str, local_appdata: str, app_subname: str, exe_name: str) -> List[Path]:
    """Fast, shallow check for JetBrains IDE executables without traversing entire hard drive."""
    exes = []
    # 1. Program Files
    jb_dir = Path(prog_files) / "JetBrains"
    if jb_dir.exists():
        try:
            for d in jb_dir.iterdir():
                if d.is_dir() and app_subname in d.name.lower():
                    for cand in [d / "bin" / f"{exe_name}64.exe", d / "bin" / f"{exe_name}.exe"]:
                        if cand.exists():
                            exes.append(cand)
        except (PermissionError, OSError):
            pass

    # 2. Local Programs
    prog_dir = Path(local_appdata) / "Programs"
    if prog_dir.exists():
        try:
            for d in prog_dir.iterdir():
                if d.is_dir() and app_subname in d.name.lower():
                    for cand in [d / "bin" / f"{exe_name}64.exe", d / f"{exe_name}.exe"]:
                        if cand.exists():
                            exes.append(cand)
        except (PermissionError, OSError):
            pass

    # 3. JetBrains Toolbox
    tb_apps = Path(local_appdata) / "JetBrains" / "Toolbox" / "apps"
    if tb_apps.exists():
        try:
            for tool in tb_apps.iterdir():
                if tool.is_dir() and app_subname in tool.name.lower():
                    for ch in tool.iterdir():
                        if ch.is_dir():
                            for ver in ch.iterdir():
                                if ver.is_dir():
                                    cand = ver / "bin" / f"{exe_name}64.exe"
                                    if cand.exists():
                                        exes.append(cand)
        except (PermissionError, OSError):
            pass

    return exes


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
        if ide_id.lower() in ide_map:
            return ide_map[ide_id.lower()]

        # Dynamic fallback: check any folder matching the ID in AppData
        clean_name = ide_id.replace("_", " ")
        return [
            appdata_path / ide_id / "User" / "settings.json",
            appdata_path / clean_name / "User" / "settings.json",
            appdata_path / ide_id.capitalize() / "User" / "settings.json",
        ]

    def discover_editor_configs(self) -> List[Dict[str, Any]]:
        """Dynamically find any editor/IDE configuration directories in %APPDATA%."""
        configs = []
        appdata = os.environ.get("APPDATA")
        appdata_path = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"

        if appdata_path.exists():
            try:
                for folder in appdata_path.iterdir():
                    if folder.is_dir() and not folder.name.startswith("."):
                        settings_file = folder / "User" / "settings.json"
                        if settings_file.exists():
                            app_id = "vscode" if folder.name.lower() == "code" else folder.name.lower().replace(" ", "_")
                            display_name = folder.name if folder.name != "Code" else "Visual Studio Code"
                            icon = "💻" if "code" in folder.name.lower() or "antigravity" in folder.name.lower() else "⚡"
                            configs.append({
                                "id": app_id,
                                "name": display_name,
                                "settings_path": str(settings_file),
                                "icon": icon,
                            })
            except (PermissionError, OSError):
                pass

        return configs

    def detect_installed_apps(self) -> List[Dict[str, Any]]:
        """
        Dynamically discover installed IDEs, Git GUI clients, and developer tools
        via the Windows Registry, JetBrains directories, AppData, and system paths.
        Optimized to use bounded shallow scans and minimal memory.
        """
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        appdata = os.environ.get("APPDATA", "")

        discovered: Dict[str, Dict[str, Any]] = {}

        # 1. Primary Well-Known Definitions with bounded/shallow lookups
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
                "exe_candidates": _find_visual_studio_exes(prog_files, prog_files_x86),
                "supports_isolation": True,
            },
            {
                "id": "rider",
                "name": "JetBrains Rider",
                "category": "IDE / Editor",
                "icon": "🔴",
                "exe_candidates": _find_jetbrains_exes(prog_files, local_appdata, "rider", "rider"),
                "supports_isolation": True,
            },
            {
                "id": "idea",
                "name": "JetBrains IntelliJ IDEA",
                "category": "IDE / Editor",
                "icon": "💡",
                "exe_candidates": _find_jetbrains_exes(prog_files, local_appdata, "idea", "idea"),
                "supports_isolation": True,
            },
            {
                "id": "pycharm",
                "name": "JetBrains PyCharm",
                "category": "IDE / Editor",
                "icon": "🐍",
                "exe_candidates": _find_jetbrains_exes(prog_files, local_appdata, "pycharm", "pycharm"),
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
                "exe_candidates": [
                    Path(local_appdata) / "gitkraken" / "gitkraken.exe",
                    Path(local_appdata) / "gitkraken" / "app" / "gitkraken.exe",
                    Path(prog_files) / "GitKraken" / "gitkraken.exe",
                ],
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

        # 2. Dynamic Registry Scanner (Discovers installed development apps with memory-safe iteration)
        if winreg is not None:
            reg_keys = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]
            keywords = [
                "git", "github", "visual studio", "rider", "intellij", "pycharm", "webstorm",
                "clion", "goland", "rustrover", "datagrip", "rubymine", "phpstorm", "code",
                "cursor", "windsurf", "eclipse", "sublime merge", "sourcetree", "gitkraken",
                "vscodium", "fleet", "positron", "antigravity", "trae", "fork", "tower",
                "smartgit", "gitextensions", "tortoisegit", "lazygit", "claude code", "aider",
                "copilot", "devin"
            ]
            ignore = [
                "pack", "sdk", "runtime", "diagnostic", "wmi", "setup", "helper", "intellisense",
                "toolset", "coveragemsi", "fonts", "logitech", "protocolhandler", "installer",
                "tools for visual studio", "redistributable", "component", "extension",
                "prerequisites", "targeting pack", "language pack", "analyzer", "build tools"
            ]

            for root_h, subkey in reg_keys:
                try:
                    with winreg.OpenKey(root_h, subkey) as key:
                        num_subkeys, _, _ = winreg.QueryInfoKey(key)
                        for i in range(min(num_subkeys, 500)):  # Bounded to 500 keys max per root
                            try:
                                sub_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, sub_name) as app_key:
                                    try:
                                        name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                                    except Exception:
                                        continue
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
                                            is_git_gui = any(g in name_l for g in ["gitkraken", "sourcetree", "sublime merge", "fork", "tower", "smartgit", "gitextensions", "tortoisegit", "lazygit", "github desktop"])
                                            is_cli_tool = any(c in name_l for c in ["claude code", "aider", "copilot", "git for windows"]) or name_l == "git"
                                            category = "Git GUI Client" if is_git_gui else ("CLI / AI Agent" if is_cli_tool else "IDE / Editor")
                                            icon = "🐙" if is_git_gui else ("🤖" if is_cli_tool else ("💻" if "code" in name_l or "antigravity" in name_l else "⚡"))
                                            discovered[app_id] = {
                                                "id": app_id,
                                                "name": name,
                                                "category": category,
                                                "icon": icon,
                                                "exe_path": loc or "System Path",
                                                "supports_isolation": "code" in name_l or "cursor" in name_l or "windsurf" in name_l or "antigravity" in name_l or "trae" in name_l,
                                            }
                            except Exception:
                                pass
                except Exception:
                    pass

        # 3. Dynamic JetBrains Directory Scanner (Bounded shallow scan)
        jetbrains_roots = [
            Path(appdata) / "JetBrains",
            Path(local_appdata) / "JetBrains" / "Toolbox" / "apps",
            Path(prog_files) / "JetBrains",
        ]
        for jb_root in jetbrains_roots:
            if jb_root.exists():
                try:
                    for folder in jb_root.iterdir():
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
                except (PermissionError, OSError):
                    pass

        return list(discovered.values())

    def get_ide_github_accounts(self) -> List[Dict[str, Any]]:
        """Extract GitHub accounts configured inside external IDEs with memory guards."""
        accounts: List[Dict[str, Any]] = []
        appdata = os.environ.get("APPDATA", "")
        jetbrains_dir = Path(appdata) / "JetBrains"
        if jetbrains_dir.exists():
            try:
                for folder in jetbrains_dir.iterdir():
                    if folder.is_dir():
                        xml_file = folder / "options" / "github.xml"
                        if xml_file.exists():
                            try:
                                # Memory check: Skip if file is unusually large (> 200KB)
                                if xml_file.stat().st_size > 200_000:
                                    continue
                                ide_name = folder.name
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
            except (PermissionError, OSError):
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