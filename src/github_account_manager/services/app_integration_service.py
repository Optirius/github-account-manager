"""Universal Service for automatically detecting and managing Git & GitHub applications across Windows, macOS, and Linux."""
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from github_account_manager.models import FolderMapping
from github_account_manager.platform import PlatformAdapter, get_platform_adapter
from github_account_manager.utils import safe_subprocess_run

logger = logging.getLogger(__name__)


class AppIntegrationService:
    def __init__(self, platform: Optional[PlatformAdapter] = None):
        self.platform = platform or get_platform_adapter()

    # --- Universal App Detection ---

    def detect_all_installed_apps(self) -> List[Dict[str, Any]]:
        """
        Automatically scan and detect all installed IDEs, Git GUI clients,
        CLI tools, and Credential Managers on this operating system.
        """
        apps: List[Dict[str, Any]] = []

        # 1. VS Code Family (VS Code, Cursor, Windsurf, VS Code Insiders, VSCodium)
        vscode_variants = [
            ("vscode", "Visual Studio Code", "💻"),
            ("cursor", "Cursor AI Editor", "✨"),
            ("windsurf", "Windsurf AI Editor", "🏄"),
            ("vscode_insiders", "VS Code Insiders", "🔮"),
            ("vscodium", "VSCodium", "🛡️"),
        ]

        for app_id, name, icon in vscode_variants:
            cand_paths = self.platform.get_ide_settings_paths(app_id)
            settings_p = next((p for p in cand_paths if p.parent.exists()), cand_paths[0] if cand_paths else None)

            if settings_p and (settings_p.parent.exists() or shutil.which(app_id) or shutil.which(app_id.replace("_", "-"))):
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
                    "description": f"Settings: {settings_p.name}. Disabling built-in GitHub auth forces {name} to use folder-specific accounts and SSH keys.",
                })

        # 2. Add other detected platform apps (GitHub Desktop, Git CLI, etc.)
        for extra_app in self.platform.detect_installed_apps():
            if not any(a["id"] == extra_app["id"] for a in apps):
                apps.append({
                    "id": extra_app["id"],
                    "name": extra_app["name"],
                    "icon": extra_app["icon"],
                    "category": extra_app["category"],
                    "installed": True,
                    "path": extra_app.get("exe_path") or "System Path",
                    "settings_path": None,
                    "supports_isolation": extra_app.get("supports_isolation", False),
                    "is_isolated": True,
                    "status_badge": "Folder & SSH Compatible",
                    "badge_variant": "active",
                    "description": f"{extra_app['name']} respects repository .gitconfig and SSH remotes (git@github.com).",
                })

        return apps

    def _check_vscode_family_settings(self, settings_file: Path) -> Tuple[bool, Optional[bool], Optional[bool]]:
        """Check if an editor's settings.json has github.gitAuthentication disabled."""
        if not settings_file.exists():
            return False, None, None

        try:
            content = settings_file.read_text(encoding="utf-8")
            data = json.loads(content)
            git_auth = data.get("github.gitAuthentication")
            term_auth = data.get("git.terminalAuthentication")

            is_isolated = (git_auth is False)
            return is_isolated, git_auth, term_auth
        except Exception as e:
            logger.debug(f"Could not parse {settings_file}: {e}")
            return False, None, None

    # --- IDE Isolation Handlers (VS Code, Cursor, Windsurf, etc.) ---

    def apply_isolation_to_app(self, app_id: str) -> Tuple[bool, str]:
        """Apply folder isolation settings to a specific IDE (VS Code, Cursor, etc.)."""
        cand_paths = self.platform.get_ide_settings_paths(app_id)
        if not cand_paths:
            return False, f"Configuration path for '{app_id}' not found on {self.platform.os_name}."

        settings_path = next((p for p in cand_paths if p.parent.exists()), cand_paths[0])

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
        cand_paths = self.platform.get_ide_settings_paths(app_id)
        settings_path = next((p for p in cand_paths if p.exists()), None)
        if not settings_path:
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

    # --- OS Credential Store (Windows Vault / macOS Keychain / Linux Secret Service) ---

    def list_windows_git_credentials(self) -> List[Dict[str, str]]:
        """List cached GitHub/Git credentials stored in the OS credential store."""
        raw_creds = self.platform.list_git_credentials()
        creds = []
        for c in raw_creds:
            creds.append({
                "Target": c.get("target", "Unknown"),
                "Type": c.get("type", "Generic"),
                "User": c.get("user", "None"),
                "IsConflicting": str(c.get("is_conflicting", False)),
            })
        return creds

    def delete_windows_git_credential(self, target: str) -> Tuple[bool, str]:
        """Delete a conflicting Git credential entry from the OS credential store."""
        success = self.platform.delete_git_credential(target)
        if success:
            return True, f"Successfully deleted credential: {target}"
        return False, f"Failed to delete credential: {target}"

    def delete_all_conflicting_credentials(self) -> Tuple[int, List[str]]:
        """Delete all cached github.com credentials."""
        creds = self.list_windows_git_credentials()
        deleted_count = 0
        messages = []

        for cred in creds:
            target = cred.get("Target", "")
            if "github" in target.lower():
                success, msg = self.delete_windows_git_credential(target)
                if success:
                    deleted_count += 1
                    messages.append(f"✓ Removed: {target}")
                else:
                    messages.append(f"✗ Failed: {target} ({msg})")

        return deleted_count, messages

    def get_ide_github_accounts(self) -> List[Dict[str, Any]]:
        """Return GitHub accounts logged in to external IDEs (such as JetBrains Rider / IntelliJ / PyCharm)."""
        return self.platform.get_ide_github_accounts()

    # --- Repository Remote Scanner & HTTPS -> SSH Protocol Converter ---

    def scan_repositories(self, folder_mappings: List[FolderMapping]) -> List[Dict[str, Any]]:
        """
        Scan all mapped workspace directories for git repositories,
        checking their remote protocol (HTTPS vs SSH) and account alignment.
        """
        repos: List[Dict[str, Any]] = []

        for mapping in folder_mappings:
            root = Path(mapping.folder_path)
            if not root.exists():
                continue

            # Check if root itself is a repo
            if (root / ".git").exists():
                self._inspect_and_add_repo(root, mapping, repos)

            # Scan child directories (up to depth 2)
            try:
                for child in root.iterdir():
                    if child.is_dir() and (child / ".git").exists():
                        self._inspect_and_add_repo(child, mapping, repos)
                    elif child.is_dir() and not child.name.startswith("."):
                        try:
                            for grandchild in child.iterdir():
                                if grandchild.is_dir() and (grandchild / ".git").exists():
                                    self._inspect_and_add_repo(grandchild, mapping, repos)
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError) as e:
                logger.debug(f"Permission error scanning {root}: {e}")

        return repos

    def _inspect_and_add_repo(self, repo_path: Path, mapping: FolderMapping, repos: List[Dict[str, Any]]) -> None:
        """Inspect a single git repository and append its info to repos list."""
        if any(r["path"] == str(repo_path) for r in repos):
            return

        remote_url = self._get_repo_remote_url(repo_path)
        if not remote_url:
            return

        is_ssh = remote_url.startswith("git@") or "ssh://" in remote_url
        is_https = remote_url.startswith("https://") or remote_url.startswith("http://")

        owner_repo = self._parse_owner_repo(remote_url)

        repos.append({
            "name": repo_path.name,
            "path": str(repo_path),
            "folder_mapping": mapping.folder_path,
            "account_id": mapping.account_id,
            "remote_url": remote_url,
            "owner_repo": owner_repo,
            "is_ssh": is_ssh,
            "is_https": is_https,
            "protocol": "SSH" if is_ssh else ("HTTPS" if is_https else "Other"),
            "status_badge": "SSH (Isolated ✓)" if is_ssh else "HTTPS (May Conflict ⚠️)",
            "badge_variant": "active" if is_ssh else "warning",
            "needs_conversion": is_https,
        })

    def _get_repo_remote_url(self, repo_path: Path) -> Optional[str]:
        """Query git remote get-url origin for a repository."""
        try:
            res = safe_subprocess_run(
                ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=4,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass

        # Fallback: parse .git/config directly
        git_config = repo_path / ".git" / "config"
        if git_config.exists():
            try:
                content = git_config.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r'\[remote\s+"origin"\][^\[]*url\s*=\s*(.+)', content, re.MULTILINE)
                if m:
                    return m.group(1).strip()
            except Exception:
                pass
        return None

    def _parse_owner_repo(self, url: str) -> Optional[str]:
        """Extract 'owner/repo' from GitHub HTTPS or SSH URL."""
        if not url:
            return ""
        m = re.search(r"github(?:\-[a-zA-Z0-9_\-]+)?\.com?[:/]([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\.\-]+)", url)
        if m:
            clean = m.group(1)
            if clean.endswith(".git"):
                clean = clean[:-4]
            return clean
        return None

    def convert_repo_remote(
        self,
        repo_path: str,
        to_protocol: str = "ssh",
        account_slug: Optional[str] = None,
    ) -> Tuple[bool, str]:
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
            res = safe_subprocess_run(
                ["git", "-C", str(p), "remote", "set-url", "origin", new_url],
                capture_output=True,
                text=True,
                timeout=6,
            )
            if res.returncode == 0:
                return True, f"Converted remote to {new_url}"
            return False, f"Git error: {res.stderr.strip()}"
        except Exception as e:
            return False, f"Failed to set remote URL: {e}"

    def convert_all_repos_to_ssh(self, folder_mappings: List[FolderMapping]) -> Tuple[int, List[str]]:
        """Scan and convert all HTTPS repositories in mapped folders to clean SSH."""
        repos = self.scan_repositories(folder_mappings)
        converted = 0
        messages = []

        for repo in repos:
            if repo["is_https"]:
                success, msg = self.convert_repo_remote(repo["path"], to_protocol="ssh")
                if success:
                    converted += 1
                    messages.append(f"✓ {repo['name']}: {msg}")
                else:
                    messages.append(f"✗ {repo['name']}: {msg}")

        return converted, messages