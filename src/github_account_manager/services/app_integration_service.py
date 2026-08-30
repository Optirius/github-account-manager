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
    # Common massive build/dependency directories to ignore during repository scans to prevent memory/CPU thrashing
    IGNORED_DIRS = {
        "node_modules", ".venv", "venv", "env", ".env", "target", "build", "dist",
        "bin", "obj", "__pycache__", ".git", ".idea", ".vscode", ".cargo", "vendor",
        ".cache", ".npm", "coverage", ".pytest_cache", ".next", ".nuxt", "out",
        "$recycle.bin", "system volume information", "appdata", "library", "temp", "tmp"
    }

    def __init__(self, platform: Optional[PlatformAdapter] = None):
        self.platform = platform or get_platform_adapter()

    # --- Universal App Detection ---

    @staticmethod
    def _normalize_app_name(name: str) -> str:
        n = name.lower().strip()
        if "visual studio code" in n or n == "code":
            return "visual studio code"
        if "cursor" in n:
            return "cursor"
        if "windsurf" in n:
            return "windsurf"
        if "antigravity ide" in n:
            return "antigravity ide"
        elif "antigravity" in n:
            return "antigravity"
        if "vscodium" in n:
            return "vscodium"
        if "github desktop" in n:
            return "github desktop"
        if "git for windows" in n or n == "git":
            return "git for windows"
        if "visual studio" in n and "code" not in n:
            return "microsoft visual studio"
        return n

    def detect_all_installed_apps(self) -> List[Dict[str, Any]]:
        """
        Dynamically scan and detect ANY installed code editors, IDEs, Git GUI clients,
        CLI developer tools, and AI coding agents on this operating system.
        """
        discovered: Dict[str, Dict[str, Any]] = {}

        # 1. Primary Well-Known Platform Lookup via get_ide_settings_paths
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
                norm_key = self._normalize_app_name(name)
                discovered[norm_key] = {
                    "id": app_id,
                    "name": name,
                    "icon": icon,
                    "category": "ide",
                    "installed": True,
                    "path": str(settings_p.parent.parent) if settings_p else "System Path",
                    "settings_path": str(settings_p) if settings_p else None,
                    "supports_isolation": True,
                    "is_isolated": is_isolated,
                    "git_auth_disabled": git_auth is False,
                    "terminal_auth_disabled": term_auth is False,
                    "status_badge": "Folder-Aware (Isolated ✓)" if is_isolated else "Account Interception Active ⚠️",
                    "badge_variant": "active" if is_isolated else "warning",
                    "description": f"Settings: {settings_p.name if settings_p else 'settings.json'}. Disabling built-in GitHub auth forces {name} to use folder-specific accounts and SSH keys.",
                }

        # 2. Dynamic Discovery of ALL other Installed Code Editors (Antigravity, Trae, Positron, etc.)
        for dynamic_editor in self.platform.discover_editor_configs():
            settings_p = Path(dynamic_editor["settings_path"])
            if settings_p.exists():
                name = dynamic_editor["name"]
                norm_key = self._normalize_app_name(name)
                if norm_key in discovered:
                    continue
                is_isolated, git_auth, term_auth = self._check_vscode_family_settings(settings_p)
                app_id = dynamic_editor["id"]
                discovered[norm_key] = {
                    "id": app_id,
                    "name": name,
                    "icon": dynamic_editor.get("icon", "💻"),
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
                    "description": f"Settings: {settings_p.name}. Disabling built-in GitHub auth forces {name} to respect folder accounts and SSH keys.",
                }

        # 3. Add other dynamically detected platform apps (JetBrains IDEs, Visual Studio, Git GUI Clients, AI/CLI tools)
        for extra_app in self.platform.detect_installed_apps():
            norm_key = self._normalize_app_name(extra_app["name"])
            if norm_key in discovered:
                existing = discovered[norm_key]
                if (not existing.get("path") or existing.get("path") == "System Path") and extra_app.get("exe_path") and extra_app.get("exe_path") != "System Path":
                    existing["path"] = extra_app["exe_path"]
                continue

            app_id = extra_app["id"]
            settings_cand = None
            if extra_app.get("supports_isolation"):
                cand_paths = self.platform.get_ide_settings_paths(app_id)
                settings_cand = next((p for p in cand_paths if p.exists()), None)

            is_isolated = True
            if settings_cand:
                is_iso, _, _ = self._check_vscode_family_settings(settings_cand)
                is_isolated = is_iso

            discovered[norm_key] = {
                "id": app_id,
                "name": extra_app["name"],
                "icon": extra_app["icon"],
                "category": extra_app["category"],
                "installed": True,
                "path": extra_app.get("exe_path") or "System Path",
                "settings_path": str(settings_cand) if settings_cand else None,
                "supports_isolation": extra_app.get("supports_isolation", False) or (settings_cand is not None),
                "is_isolated": is_isolated,
                "status_badge": "Folder & SSH Compatible" if is_isolated else "Account Interception Active ⚠️",
                "badge_variant": "active" if is_isolated else "warning",
                "description": f"{extra_app['name']} integrates with Git and respects repository .gitconfig and SSH remotes (git@github.com).",
            }

        return list(discovered.values())

    def _check_vscode_family_settings(self, settings_file: Path) -> Tuple[bool, Optional[bool], Optional[bool]]:
        """Check if an editor's settings.json has github.gitAuthentication disabled."""
        if not settings_file.exists():
            return False, None, None

        try:
            if settings_file.stat().st_size > 100_000:
                return False, None, None
            content = settings_file.read_text(encoding="utf-8")
            data = json.loads(content)
            git_auth = data.get("github.gitAuthentication")
            term_auth = data.get("git.terminalAuthentication")

            is_isolated = (git_auth is False)
            return is_isolated, git_auth, term_auth
        except Exception as e:
            logger.debug(f"Could not parse {settings_file}: {e}")
            return False, None, None

    # --- IDE Isolation Handlers (VS Code, Cursor, Windsurf, Antigravity, Trae, etc.) ---

    def apply_isolation_to_app(self, app_id: str, settings_path_override: Optional[str] = None) -> Tuple[bool, str]:
        """Apply folder isolation settings to ANY discovered IDE or editor (VS Code, Cursor, Antigravity, Trae, etc.)."""
        settings_path = None
        if settings_path_override:
            p = Path(settings_path_override)
            if p.parent.exists():
                settings_path = p

        if not settings_path:
            cand_paths = self.platform.get_ide_settings_paths(app_id)
            if cand_paths:
                settings_path = next((p for p in cand_paths if p.parent.exists()), cand_paths[0])

        if not settings_path:
            return False, f"Configuration path for '{app_id}' not found on {self.platform.os_name}."

        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if settings_path.exists():
                try:
                    shutil.copy2(settings_path, settings_path.with_suffix(".json.bak"))
                except Exception:
                    pass
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
        """Apply folder isolation to ALL detected IDEs and editors on this device."""
        apps = self.detect_all_installed_apps()
        configured = 0
        messages = []

        for app in apps:
            if app.get("supports_isolation") and app.get("installed"):
                success, msg = self.apply_isolation_to_app(app["id"], app.get("settings_path"))
                if success:
                    configured += 1
                    messages.append(f"✓ {app['name']}: Configured")
                else:
                    messages.append(f"✗ {app['name']}: {msg}")

        return configured, messages

    def restore_defaults_for_app(self, app_id: str, settings_path_override: Optional[str] = None) -> Tuple[bool, str]:
        """Restore default Git authentication behavior for ANY discovered IDE or editor."""
        settings_path = None
        if settings_path_override:
            p = Path(settings_path_override)
            if p.exists():
                settings_path = p

        if not settings_path:
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

    def delete_windows_credential(self, target: str) -> Tuple[bool, str]:
        """Alias for delete_windows_git_credential for UI compatibility."""
        return self.delete_windows_git_credential(target)

    def enable_git_credential_use_http_path(self) -> Tuple[bool, str]:
        """Configure git config --global credential.useHttpPath true so HTTPS credentials are scoped per repo path."""
        try:
            res = safe_subprocess_run(
                ["git", "config", "--global", "credential.useHttpPath", "true"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return True, "Enabled 'credential.useHttpPath = true' in global Git config."
            return False, f"Git error: {res.stderr.strip()}"
        except Exception as e:
            return False, f"Failed to set credential.useHttpPath: {e}"

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

    def scan_repositories(
        self,
        folder_mappings: List[FolderMapping],
        max_repos: int = 100,
        max_items_per_folder: int = 250,
    ) -> List[Dict[str, Any]]:
        """
        Scan all mapped workspace directories for git repositories with memory safeguards:
        - Skips heavy dependency and build directories (node_modules, .venv, target, dist, etc.)
        - Direct in-memory reading of .git/config (zero subprocess spawning)
        - Depth-bounded search (max depth 2)
        - Hard limits on items scanned per folder and total repositories
        """
        repos: List[Dict[str, Any]] = []

        for mapping in folder_mappings:
            if len(repos) >= max_repos:
                break

            root = Path(mapping.folder_path)
            if not root.exists():
                continue

            # Check if root itself is a repo
            if (root / ".git").exists():
                self._inspect_and_add_repo(root, mapping, repos)
                if len(repos) >= max_repos:
                    break

            # Scan child directories (up to depth 2) with safe bounds
            try:
                scanned_count = 0
                for child in root.iterdir():
                    scanned_count += 1
                    if scanned_count > max_items_per_folder or len(repos) >= max_repos:
                        break

                    child_name_l = child.name.lower()
                    if child.name.startswith(".") or child_name_l in self.IGNORED_DIRS:
                        continue

                    if child.is_dir():
                        if (child / ".git").exists():
                            self._inspect_and_add_repo(child, mapping, repos)
                        else:
                            # Grandchild scan (depth 2)
                            try:
                                sub_scanned = 0
                                for grandchild in child.iterdir():
                                    sub_scanned += 1
                                    if sub_scanned > 50 or len(repos) >= max_repos:
                                        break
                                    gc_name_l = grandchild.name.lower()
                                    if grandchild.name.startswith(".") or gc_name_l in self.IGNORED_DIRS:
                                        continue
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
        """Query origin remote URL for a repository with fast in-memory file parsing first."""
        # 1. Fast in-memory parsing of .git/config (zero subprocess spawning)
        git_target = repo_path / ".git"
        git_config = None
        if git_target.is_dir():
            git_config = git_target / "config"
        elif git_target.is_file():
            # Submodule or worktree pointing to gitdir: ...
            try:
                line = git_target.read_text(encoding="utf-8", errors="ignore").strip()
                if line.startswith("gitdir:"):
                    gitdir_path = (repo_path / line.split("gitdir:", 1)[1].strip()).resolve()
                    git_config = gitdir_path / "config"
            except Exception:
                pass

        if git_config and git_config.exists():
            try:
                # Memory guard: skip if config is unusually massive (> 50KB)
                if git_config.stat().st_size < 50_000:
                    content = git_config.read_text(encoding="utf-8", errors="ignore")
                    m = re.search(r'\[remote\s+"origin"\][^\[]*url\s*=\s*(.+)', content, re.MULTILINE)
                    if m:
                        return m.group(1).strip()
            except Exception:
                pass

        # 2. Fallback: query git subprocess if direct file read was inconclusive
        try:
            res = safe_subprocess_run(
                ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass

        return None

    def _parse_owner_repo(self, url: str) -> Optional[str]:
        """Extract 'owner/repo' from GitHub HTTPS, standard SSH, or custom alias SSH URLs."""
        if not url:
            return ""
        m = re.search(r"(?:https?://|git@|ssh://git@)[^:/]+[:/]([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\.\-]+)", url)
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