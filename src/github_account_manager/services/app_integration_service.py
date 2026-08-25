"""Universal Service for automatically detecting and managing all Git & GitHub applications on Windows."""
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from github_account_manager.models import FolderMapping

logger = logging.getLogger(__name__)


class AppIntegrationService:
    def __init__(self):
        self.appdata = Path(os.getenv("APPDATA", "")) if os.getenv("APPDATA") else None
        self.localappdata = Path(os.getenv("LOCALAPPDATA", "")) if os.getenv("LOCALAPPDATA") else None
        self.userprofile = Path(os.getenv("USERPROFILE", "")) if os.getenv("USERPROFILE") else None

    # --- Universal App Detection ---

    def detect_all_installed_apps(self) -> List[Dict[str, Any]]:
        """
        Automatically scan and detect all installed IDEs, Git GUI clients,
        CLI tools, and Credential Managers on the Windows device.
        """
        apps: List[Dict[str, Any]] = []

        # 1. VS Code Family (VS Code, Cursor, Windsurf, VS Code Insiders, VSCodium)
        vscode_variants = [
            ("vscode", "Visual Studio Code", "💻", self.appdata / "Code" / "User" / "settings.json" if self.appdata else None),
            ("cursor", "Cursor AI Editor", "✨", self.appdata / "Cursor" / "User" / "settings.json" if self.appdata else None),
            ("windsurf", "Windsurf AI Editor", "🏄", self.appdata / "Windsurf" / "User" / "settings.json" if self.appdata else None),
            ("vscode_insiders", "VS Code Insiders", "🔮", self.appdata / "Code - Insiders" / "User" / "settings.json" if self.appdata else None),
            ("vscodium", "VSCodium", "🛡️", self.appdata / "VSCodium" / "User" / "settings.json" if self.appdata else None),
        ]

        for app_id, name, icon, settings_p in vscode_variants:
            if settings_p and settings_p.parent.exists():
                is_isolated, git_auth, term_auth = self._check_vscode_family_settings(settings_p)
                apps.append({
                    "id": app_id,
                    "name": name,
                    "icon": icon,
                    "category": "ide",
                    "installed": True,
                    "path": str(settings_p.parent.parent),
                    "settings_path": str(settings_p),
                    "supports_isolation": True,
                    "is_isolated": is_isolated,
                    "git_auth_disabled": git_auth is False,
                    "terminal_auth_disabled": term_auth is False,
                    "status_badge": "Folder-Aware (Isolated ✓)" if is_isolated else "Account Interception Active ⚠️",
                    "badge_variant": "active" if is_isolated else "warning",
                    "description": f"Settings: {settings_p.name} in AppData. Disabling built-in GitHub auth forces {name} to use folder-specific accounts and SSH keys.",
                })

        # 2. GitHub Desktop
        gh_desktop_path = self.localappdata / "GitHubDesktop" if self.localappdata else None
        if gh_desktop_path and gh_desktop_path.exists():
            apps.append({
                "id": "github_desktop",
                "name": "GitHub Desktop",
                "icon": "🐙",
                "category": "git_client",
                "installed": True,
                "path": str(gh_desktop_path),
                "settings_path": str(self.appdata / "GitHub Desktop" if self.appdata else gh_desktop_path),
                "supports_isolation": False,
                "is_isolated": True,
                "status_badge": "Folder & SSH Compatible",
                "badge_variant": "active",
                "description": "GitHub Desktop respects repository .gitconfig and SSH remotes (git@github.com). Converted SSH repositories will automatically use each folder's assigned SSH key.",
            })

        # 3. Visual Studio (2019/2022)
        vs_ide_path = self.localappdata / "Microsoft" / "VisualStudio" if self.localappdata else None
        if vs_ide_path and vs_ide_path.exists():
            apps.append({
                "id": "visual_studio",
                "name": "Visual Studio (IDE)",
                "icon": "🖥️",
                "category": "ide",
                "installed": True,
                "path": str(vs_ide_path),
                "settings_path": None,
                "supports_isolation": False,
                "is_isolated": False,
                "status_badge": "Uses Windows Credential Vault",
                "badge_variant": "info",
                "description": "Visual Studio authenticates HTTPS remotes through Windows Credential Manager. Use SSH remotes to ensure strict folder isolation.",
            })

        # 4. JetBrains IDEs (IntelliJ, PyCharm, WebStorm, CLion, Rider, etc.)
        jetbrains_path = self.appdata / "JetBrains" if self.appdata else None
        if jetbrains_path and jetbrains_path.exists():
            jb_dirs = [d.name for d in jetbrains_path.iterdir() if d.is_dir()]
            apps.append({
                "id": "jetbrains",
                "name": f"JetBrains IDEs ({', '.join(jb_dirs[:3])})",
                "icon": "🧠",
                "category": "ide",
                "installed": True,
                "path": str(jetbrains_path),
                "settings_path": None,
                "supports_isolation": False,
                "is_isolated": True,
                "status_badge": "Folder & Native Git Compatible",
                "badge_variant": "active",
                "description": "JetBrains IDEs use Native Git executable and strictly follow ~/.gitconfig includeIf folder rules and SSH commands.",
            })

        # 5. Git CLI & Git Credential Manager (GCM)
        gcm_installed = shutil.which("git-credential-manager") is not None or shutil.which("git") is not None
        creds = self.list_windows_git_credentials()
        apps.append({
            "id": "gcm",
            "name": "Git Credential Manager & Windows Vault",
            "icon": "🔐",
            "category": "credential_helper",
            "installed": gcm_installed,
            "path": "Windows Credential Manager",
            "settings_path": "~/.gitconfig (credential.helper = manager)",
            "supports_isolation": False,
            "is_isolated": len(creds) == 0,
            "status_badge": f"{len(creds)} Cached GitHub Credentials" if creds else "Vault Clean (No Overrides ✓)",
            "badge_variant": "warning" if creds else "active",
            "description": "Manages HTTPS authentication tokens for all Windows command-line Git tools, Visual Studio, and terminal shells.",
            "cached_credentials": creds,
        })

        return apps

    def _check_vscode_family_settings(self, settings_path: Path) -> Tuple[bool, Any, Any]:
        """Check if a VS Code derivative has GitHub auth disabled."""
        if not settings_path.exists():
            return False, None, None
        try:
            content = settings_path.read_text(encoding="utf-8")
            data = json.loads(content)
            git_auth = data.get("github.gitAuthentication", True)
            term_auth = data.get("git.terminalAuthentication", True)
            is_isolated = (git_auth is False) and (term_auth is False)
            return is_isolated, git_auth, term_auth
        except Exception:
            return False, None, None

    # --- IDE Isolation Handlers (VS Code, Cursor, Windsurf, etc.) ---

    def apply_isolation_to_app(self, app_id: str) -> Tuple[bool, str]:
        """Apply folder isolation settings to a specific IDE (VS Code, Cursor, etc.)."""
        settings_map = {
            "vscode": self.appdata / "Code" / "User" / "settings.json" if self.appdata else None,
            "cursor": self.appdata / "Cursor" / "User" / "settings.json" if self.appdata else None,
            "windsurf": self.appdata / "Windsurf" / "User" / "settings.json" if self.appdata else None,
            "vscode_insiders": self.appdata / "Code - Insiders" / "User" / "settings.json" if self.appdata else None,
            "vscodium": self.appdata / "VSCodium" / "User" / "settings.json" if self.appdata else None,
        }

        settings_path = settings_map.get(app_id)
        if not settings_path:
            return False, f"Configuration path for '{app_id}' not found."

        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if settings_path.exists():
                shutil.copy2(settings_path, settings_path.with_suffix(".json.bak"))
                try:
                    content = settings_path.read_text(encoding="utf-8")
                    data = json.loads(content)
                except Exception:
                    data = {}

            data["github.gitAuthentication"] = False
            data["git.terminalAuthentication"] = False

            settings_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
            return True, f"Applied strict folder isolation to {settings_path.parent.parent.name}."
        except Exception as e:
            return False, f"Failed to configure {app_id}: {e}"

    def apply_isolation_to_all_ides(self) -> Tuple[int, List[str]]:
        """Apply folder isolation to all installed VS Code family IDEs on this device."""
        apps = self.detect_all_installed_apps()
        configured = 0
        messages = []

        for app in apps:
            if app.get("supports_isolation") and app.get("installed"):
                success, msg = self.apply_isolation_to_app(app["id"])
                if success:
                    configured += 1
                    messages.append(f"✓ {app['name']}: Configured")
                else:
                    messages.append(f"✗ {app['name']}: {msg}")

        return configured, messages

    def restore_defaults_for_app(self, app_id: str) -> Tuple[bool, str]:
        """Restore default Git authentication behavior for a specific IDE."""
        settings_map = {
            "vscode": self.appdata / "Code" / "User" / "settings.json" if self.appdata else None,
            "cursor": self.appdata / "Cursor" / "User" / "settings.json" if self.appdata else None,
            "windsurf": self.appdata / "Windsurf" / "User" / "settings.json" if self.appdata else None,
            "vscode_insiders": self.appdata / "Code - Insiders" / "User" / "settings.json" if self.appdata else None,
            "vscodium": self.appdata / "VSCodium" / "User" / "settings.json" if self.appdata else None,
        }

        settings_path = settings_map.get(app_id)
        if not settings_path or not settings_path.exists():
            return False, "Settings file not found."

        try:
            content = settings_path.read_text(encoding="utf-8")
            data = json.loads(content)
            data.pop("github.gitAuthentication", None)
            data.pop("git.terminalAuthentication", None)

            settings_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
            return True, f"Restored default authentication settings for {settings_path.parent.parent.name}."
        except Exception as e:
            return False, f"Failed to restore {app_id}: {e}"

    # --- Windows Credential Manager (GCM) ---

    def list_windows_git_credentials(self) -> List[Dict[str, str]]:
        """List cached GitHub/Git credentials stored in Windows Credential Manager."""
        try:
            res = subprocess.run(["cmdkey", "/list"], capture_output=True, text=True, timeout=8)
            output = res.stdout

            creds = []
            current: Dict[str, str] = {}
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("Target:"):
                    if current and "Target" in current:
                        creds.append(current)
                    raw_target = line.split("Target:", 1)[1].strip()
                    current = {"Target": raw_target}
                elif line.startswith("Type:"):
                    current["Type"] = line.split("Type:", 1)[1].strip()
                elif line.startswith("User:"):
                    current["User"] = line.split("User:", 1)[1].strip()

            if current and "Target" in current:
                creds.append(current)

            github_creds = [
                c for c in creds
                if "github" in c.get("Target", "").lower() or "git:" in c.get("Target", "").lower()
            ]
            return github_creds
        except Exception as e:
            logger.error(f"Failed to query cmdkey: {e}")
            return []

    def delete_windows_credential(self, target: str) -> Tuple[bool, str]:
        """Delete a cached credential from Windows Credential Manager."""
        clean_target = target.strip()
        if clean_target.startswith("LegacyGeneric:target="):
            clean_target = clean_target[len("LegacyGeneric:target="):]

        try:
            res = subprocess.run(["cmdkey", f"/delete:{clean_target}"], capture_output=True, text=True, timeout=8)
            if res.returncode != 0 and target != clean_target:
                res = subprocess.run(["cmdkey", f"/delete:{target}"], capture_output=True, text=True, timeout=8)

            if res.returncode == 0:
                return True, f"Deleted credential '{clean_target}' from Windows Credential Manager."
            return False, res.stderr or res.stdout or "Failed to delete credential."
        except Exception as e:
            return False, str(e)

    def enable_git_credential_use_http_path(self) -> Tuple[bool, str]:
        """Configure Git to differentiate HTTPS credentials per repository path."""
        try:
            res = subprocess.run(
                ["git", "config", "--global", "credential.useHttpPath", "true"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            if res.returncode == 0:
                return True, "Configured 'credential.useHttpPath = true' globally."
            return False, res.stderr or "Failed to set git config."
        except Exception as e:
            return False, str(e)

    # --- Repository Remote Scanner & Converter ---

    def scan_repositories(self, folder_mappings: List[FolderMapping]) -> List[Dict[str, Any]]:
        """
        Scan all git repositories inside user-configured folder mappings.
        Returns detailed list with remote URL, protocol, and target owner/repo.
        """
        found_repos: List[Dict[str, Any]] = []
        visited_paths = set()

        for mapping in folder_mappings:
            base_dir = Path(mapping.folder_path)
            if not base_dir.exists() or not base_dir.is_dir():
                continue

            candidates: List[Path] = []
            if (base_dir / ".git").exists():
                candidates.append(base_dir)

            try:
                for item in base_dir.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        if (item / ".git").exists():
                            candidates.append(item)
                        else:
                            try:
                                for sub in item.iterdir():
                                    if sub.is_dir() and (sub / ".git").exists():
                                        candidates.append(sub)
                            except Exception:
                                pass
            except Exception as e:
                logger.error(f"Error scanning {base_dir}: {e}")

            for repo_dir in candidates:
                norm_str = repo_dir.as_posix().lower()
                if norm_str in visited_paths:
                    continue
                visited_paths.add(norm_str)

                remote_url = self._get_repo_remote_url(repo_dir)
                protocol = "SSH" if remote_url.startswith("git@") or "ssh://" in remote_url else ("HTTPS" if remote_url.startswith("http") else "Local/None")
                owner_repo = self._parse_owner_repo(remote_url)

                found_repos.append({
                    "name": repo_dir.name,
                    "path": str(repo_dir),
                    "folder_mapping": mapping.folder_path,
                    "account_id": mapping.account_id,
                    "remote_url": remote_url,
                    "protocol": protocol,
                    "owner_repo": owner_repo,
                })

        return found_repos

    def _get_repo_remote_url(self, repo_path: Path) -> str:
        try:
            res = subprocess.run(
                ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=6,
            )
            return res.stdout.strip()
        except Exception:
            return ""

    def _parse_owner_repo(self, remote_url: str) -> str:
        if not remote_url:
            return ""
        m = re.search(r"github\.com[:/]([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\.\-]+)", remote_url)
        if m:
            clean = m.group(1)
            if clean.endswith(".git"):
                clean = clean[:-4]
            return clean
        return ""

    def convert_repo_remote(self, repo_path: str | Path, to_protocol: str = "ssh") -> Tuple[bool, str]:
        """Convert a repository remote URL between HTTPS and SSH."""
        p = Path(repo_path)
        if not p.exists() or not (p / ".git").exists():
            return False, f"Directory is not a valid git repository: {repo_path}"

        current_url = self._get_repo_remote_url(p)
        if not current_url:
            return False, "No 'origin' remote configured for this repository."

        owner_repo = self._parse_owner_repo(current_url)
        if not owner_repo:
            return False, f"Could not parse GitHub repository owner and name from: {current_url}"

        if to_protocol.lower() == "ssh":
            new_url = f"git@github.com:{owner_repo}.git"
        else:
            new_url = f"https://github.com/{owner_repo}.git"

        if current_url == new_url:
            return True, f"Remote is already using {to_protocol.upper()} ({new_url})."

        try:
            res = subprocess.run(
                ["git", "-C", str(p), "remote", "set-url", "origin", new_url],
                capture_output=True,
                text=True,
                timeout=6,
            )
            if res.returncode == 0:
                return True, f"Converted remote to {to_protocol.upper()}: {new_url}"
            return False, res.stderr or "Failed to set remote URL."
        except Exception as e:
            return False, str(e)