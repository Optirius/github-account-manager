"""Central application orchestrator coordinating data persistence, services, and sync."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from github_account_manager.config import APP_VERSION, CONFIG_FILE, DEFAULT_GITCONFIG, DEFAULT_SSH_DIR
from github_account_manager.models import Account, AppSettings, FolderMapping, SSHKeyInfo
from github_account_manager.services.app_integration_service import AppIntegrationService
from github_account_manager.services.git_service import GitService
from github_account_manager.services.github_service import GitHubService
from github_account_manager.services.ssh_service import SSHService
from github_account_manager.services.update_service import UpdateInfo, UpdateService

logger = logging.getLogger(__name__)


class AccountManager:
    def __init__(
        self,
        config_file: Optional[Path] = None,
        gitconfig_path: Optional[Path] = None,
        ssh_dir: Optional[Path] = None,
    ):
        self.config_file = config_file or CONFIG_FILE
        home_override = gitconfig_path.parent if gitconfig_path else None
        self.git_service = GitService(gitconfig_path or DEFAULT_GITCONFIG, home_dir=home_override)
        self.ssh_service = SSHService(ssh_dir or DEFAULT_SSH_DIR)
        self.github_service = GitHubService()
        self.app_service = AppIntegrationService()
        self.update_service = UpdateService(current_version=APP_VERSION)
        self.settings = self.load_settings()

        # Run auto-repair to link matching SSH keys, resolve slug collisions, and sync git config
        if not self.settings.accounts:
            self._auto_discover_existing_setup()
        else:
            self.auto_repair_and_sync()

    def load_settings(self) -> AppSettings:
        """Load settings from JSON config file or return default."""
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                return AppSettings(**data)
            except Exception as e:
                logger.error(f"Error reading {self.config_file}: {e}")
        return AppSettings()

    def save_settings(self) -> None:
        """Save current settings to JSON file and sync git if enabled."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self.config_file.write_text(
                self.settings.model_dump_json(indent=2),
                encoding="utf-8",
            )
            if self.settings.auto_sync_gitconfig:
                self.sync_git()
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def sync_git(self) -> bool:
        """Synchronize git configuration files and includeIf statements."""
        return self.git_service.sync_global_gitconfig(
            self.settings.accounts,
            self.settings.folder_mappings,
        )

    def _auto_discover_existing_setup(self) -> None:
        """Import existing .gitconfig and SSH keys on first launch."""
        ssh_keys = self.ssh_service.list_keys()

        personal_key = next((k for k in ssh_keys if "personal" in k.name.lower()), None)
        prof_key = next((k for k in ssh_keys if "prof" in k.name.lower() or "work" in k.name.lower()), None)

        created_accounts = []

        if personal_key:
            acc = Account(
                name="Personal",
                email="personal@example.com",
                git_name="Personal Developer",
                ssh_key_path=personal_key.private_key_path,
            )
            created_accounts.append(acc)

        if prof_key:
            acc = Account(
                name="Work",
                email="work@example.com",
                git_name="Work Developer",
                ssh_key_path=prof_key.private_key_path,
            )
            created_accounts.append(acc)

        if created_accounts:
            self.settings.accounts = created_accounts
            self.save_settings()

    def auto_repair_and_sync(self) -> Tuple[int, List[str]]:
        """
        Auto-discover and repair missing SSH keys, resolve duplicate profile filename collisions,
        re-bind folder mappings to appropriate accounts, and sync global gitconfig.
        Returns: (repairs_count, list_of_repair_messages)
        """
        repairs: List[str] = []
        home = Path.home()
        ssh_keys = self.ssh_service.list_keys()

        # 1. Auto-bind missing SSH keys for accounts if matching key exists in ~/.ssh
        for acc in self.settings.accounts:
            if not acc.ssh_key_path or not Path(acc.ssh_key_path).exists():
                matched_key = None
                acc_terms = [t for t in [acc.name, acc.username, acc.email.split("@")[0] if "@" in acc.email else ""] if t]
                for key in ssh_keys:
                    kname = key.name.lower()
                    if any(term.lower() in kname for term in acc_terms if len(term) > 2):
                        matched_key = key
                        break
                    # Naming fallbacks
                    if "personal" in kname and ("personal" in acc.name.lower() or "personal" in acc.email.lower()):
                        matched_key = key
                        break
                    if ("work" in kname or "prof" in kname) and ("work" in acc.name.lower() or "prof" in acc.name.lower() or "work" in acc.email.lower()):
                        matched_key = key
                        break

                if matched_key:
                    acc.ssh_key_path = matched_key.private_key_path
                    repairs.append(f"Linked SSH key '{matched_key.name}' to profile '{acc.name} ({acc.username or acc.email})'")

        # 2. Clean up legacy clashing single-slug config files (e.g. .gitconfig-tahmid-hossain)
        try:
            for item in home.glob(".gitconfig-*"):
                if not any(acc.config_filename == item.name for acc in self.settings.accounts):
                    try:
                        item.unlink()
                        repairs.append(f"Removed legacy profile file '{item.name}'")
                    except Exception:
                        pass
        except Exception:
            pass

        # 3. Save and sync global git config and full SSH alias mappings
        self.save_settings()
        self.sync_git()
        repairs.append("Synchronized global ~/.gitconfig and ~/.ssh/config with all host aliases")

        # 4. Check mapped repositories and ensure remotes and aliases are aligned
        try:
            repos = self.app_service.scan_repositories(self.settings.folder_mappings)
            for repo in repos:
                if repo.get("needs_conversion"):
                    repairs.append(f"Repository '{repo['name']}' uses HTTPS remote (can be converted to SSH via Apps tab)")
                elif repo.get("is_ssh"):
                    repairs.append(f"Repository '{repo['name']}' SSH remote verified ({repo['remote_url']})")
        except Exception:
            pass

        return len(repairs), repairs

    # --- Account Operations ---

    def add_account(
        self,
        name: str,
        email: str,
        git_name: str,
        username: str = "",
        ssh_key_path: Optional[str] = None,
    ) -> Account:
        """Add a new account profile."""
        account = Account(
            name=name.strip(),
            email=email.strip(),
            git_name=git_name.strip(),
            username=username.strip(),
            ssh_key_path=ssh_key_path.strip() if ssh_key_path else None,
        )
        self.settings.accounts.append(account)
        self.save_settings()
        return account

    def update_account(
        self,
        account_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        git_name: Optional[str] = None,
        username: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
    ) -> Optional[Account]:
        """Update account properties."""
        acc = next((a for a in self.settings.accounts if a.id == account_id), None)
        if not acc:
            return None

        if name is not None:
            acc.name = name.strip()
        if email is not None:
            acc.email = email.strip()
        if git_name is not None:
            acc.git_name = git_name.strip()
        if username is not None:
            acc.username = username.strip()
        if ssh_key_path is not None:
            acc.ssh_key_path = ssh_key_path.strip() if ssh_key_path else None

        self.save_settings()
        return acc

    def delete_account(self, account_id: str) -> bool:
        """Delete an account and its folder mappings."""
        acc = next((a for a in self.settings.accounts if a.id == account_id), None)
        if not acc:
            return False

        self.git_service.remove_account_profile_config(acc)

        self.settings.accounts = [a for a in self.settings.accounts if a.id != account_id]
        self.settings.folder_mappings = [
            m for m in self.settings.folder_mappings if m.account_id != account_id
        ]

        self.save_settings()
        return True

    # --- Folder Mappings ---

    def add_folder_mapping(self, folder_path: str, account_id: str) -> FolderMapping:
        """Add a directory to account mapping."""
        # Normalize path
        norm_input = Path(folder_path).as_posix().rstrip("/")

        # Check if mapping for this folder already exists
        existing = next(
            (m for m in self.settings.folder_mappings if Path(m.folder_path).as_posix().rstrip("/") == norm_input),
            None,
        )
        if existing:
            existing.account_id = account_id
            self.save_settings()
            return existing

        mapping = FolderMapping(folder_path=folder_path, account_id=account_id)
        self.settings.folder_mappings.append(mapping)
        self.save_settings()
        return mapping

    def remove_folder_mapping(self, mapping_id: str) -> bool:
        """Remove a directory mapping."""
        initial_len = len(self.settings.folder_mappings)
        self.settings.folder_mappings = [
            m for m in self.settings.folder_mappings if m.id != mapping_id
        ]
        if len(self.settings.folder_mappings) != initial_len:
            self.save_settings()
            return True
        return False

    def get_account_for_folder(self, target_folder: str) -> Optional[Account]:
        """Find the matching account for a given folder path."""
        target_norm = Path(target_folder).as_posix().lower().rstrip("/") + "/"
        account_map = {acc.id: acc for acc in self.settings.accounts}

        # Find the longest matching prefix
        best_match = None
        best_len = -1

        for m in self.settings.folder_mappings:
            m_norm = Path(m.folder_path).as_posix().lower().rstrip("/") + "/"
            if target_norm.startswith(m_norm) and len(m_norm) > best_len:
                best_match = account_map.get(m.account_id)
                best_len = len(m_norm)

        return best_match

    # --- SSH & GitHub Integration ---

    def test_ssh_for_account(self, account_id: str) -> Tuple[bool, str, Optional[str]]:
        """Test SSH connection for a given account's configured SSH key."""
        acc = next((a for a in self.settings.accounts if a.id == account_id), None)
        if not acc or not acc.ssh_key_path:
            return False, "No SSH key configured for this account.", None

        return self.ssh_service.test_connection(acc.ssh_key_path)

    def delete_ssh_key(self, ssh_key_path: str) -> bool:
        """Delete an SSH key file from disk and unlink from any accounts using it."""
        deleted = self.ssh_service.delete_key(ssh_key_path)
        
        # Check if any accounts used this key
        updated_any = False
        target_name = Path(ssh_key_path).name.lower()
        for acc in self.settings.accounts:
            if acc.ssh_key_path and (Path(acc.ssh_key_path).name.lower() == target_name or acc.ssh_key_path == ssh_key_path):
                acc.ssh_key_path = None
                updated_any = True

        if updated_any or deleted:
            self.save_settings()
        return deleted