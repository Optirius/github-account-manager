"""Central application orchestrator coordinating data persistence, services, and sync."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from github_account_manager.config import CONFIG_FILE, DEFAULT_GITCONFIG, DEFAULT_SSH_DIR
from github_account_manager.models import Account, AppSettings, FolderMapping, SSHKeyInfo
from github_account_manager.services.app_integration_service import AppIntegrationService
from github_account_manager.services.git_service import GitService
from github_account_manager.services.github_service import GitHubService
from github_account_manager.services.keyring_service import KeyringService
from github_account_manager.services.ssh_service import SSHService

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
        self.keyring_service = KeyringService()
        self.app_service = AppIntegrationService()
        self.settings = self.load_settings()

        # If empty settings, try auto-discovering existing accounts from system
        if not self.settings.accounts:
            self._auto_discover_existing_setup()

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
        home = Path.home()
        ssh_keys = self.ssh_service.list_keys()

        # Check for personal key
        personal_key = next((k for k in ssh_keys if "personal" in k.name.lower()), None)
        prof_key = next((k for k in ssh_keys if "prof" in k.name.lower() or "work" in k.name.lower()), None)

        created_accounts = []

        if personal_key or (home / ".gitconfig-personal").exists():
            acc = Account(
                name="Personal",
                email="tahmid95.hossain@gmail.com",
                git_name="Tahmid Hossain",
                ssh_key_path=personal_key.private_key_path if personal_key else None,
            )
            created_accounts.append(acc)

        if prof_key or (home / ".gitconfig-professional").exists():
            acc = Account(
                name="Professional",
                email="tahmid.hossain@selisegroup.com",
                git_name="Tahmid Hossain",
                ssh_key_path=prof_key.private_key_path if prof_key else None,
            )
            created_accounts.append(acc)

        if created_accounts:
            self.settings.accounts = created_accounts

            # Check for folders D:\Personal and D:\Professional
            if Path("D:/Personal").exists() and len(created_accounts) >= 1:
                self.settings.folder_mappings.append(
                    FolderMapping(folder_path="D:/Personal", account_id=created_accounts[0].id)
                )
            if Path("D:/Professional").exists() and len(created_accounts) >= 2:
                self.settings.folder_mappings.append(
                    FolderMapping(folder_path="D:/Professional", account_id=created_accounts[1].id)
                )

            self.save_settings()

    # --- Account Operations ---

    def add_account(
        self,
        name: str,
        email: str,
        git_name: str,
        username: str = "",
        ssh_key_path: Optional[str] = None,
        avatar_url: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Account:
        """Add a new account profile."""
        account = Account(
            name=name.strip(),
            email=email.strip(),
            git_name=git_name.strip(),
            username=username.strip(),
            ssh_key_path=ssh_key_path.strip() if ssh_key_path else None,
            avatar_url=avatar_url,
            is_authenticated=bool(token),
        )
        self.settings.accounts.append(account)

        if token:
            self.keyring_service.save_token(account.id, token.strip())

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
        avatar_url: Optional[str] = None,
        token: Optional[str] = None,
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
        if avatar_url is not None:
            acc.avatar_url = avatar_url

        if token is not None:
            if token.strip():
                self.keyring_service.save_token(acc.id, token.strip())
                acc.is_authenticated = True
            else:
                self.keyring_service.delete_token(acc.id)
                acc.is_authenticated = False

        self.save_settings()
        return acc

    def delete_account(self, account_id: str) -> bool:
        """Delete an account, associated tokens, and its folder mappings."""
        acc = next((a for a in self.settings.accounts if a.id == account_id), None)
        if not acc:
            return False

        self.keyring_service.delete_token(acc.id)
        self.git_service.remove_account_profile_config(acc)

        self.settings.accounts = [a for a in self.settings.accounts if a.id != account_id]
        self.settings.folder_mappings = [
            m for m in self.settings.folder_mappings if m.account_id != account_id
        ]

        self.save_settings()
        return True

    def login_with_token(self, account_id: str, token: str) -> Dict[str, Any]:
        """Validate token with GitHub API, save to keyring, and update account profile."""
        acc = next((a for a in self.settings.accounts if a.id == account_id), None)
        if not acc:
            return {"success": False, "error": "Account not found."}

        res = self.github_service.validate_token(token)
        if not res.get("success"):
            return res

        # Update account profile from GitHub API data
        acc.is_authenticated = True
        if res.get("username"):
            acc.username = res["username"]
        if res.get("avatar_url"):
            acc.avatar_url = res["avatar_url"]
        if res.get("email") and not acc.email:
            acc.email = res["email"]
        if res.get("name") and not acc.git_name:
            acc.git_name = res["name"]

        self.keyring_service.save_token(acc.id, token.strip())
        self.save_settings()
        return res

    def logout_account(self, account_id: str) -> bool:
        """Clear token from keyring and mark unauthenticated."""
        acc = next((a for a in self.settings.accounts if a.id == account_id), None)
        if not acc:
            return False

        self.keyring_service.delete_token(acc.id)
        acc.is_authenticated = False
        self.save_settings()
        return True

    def get_token(self, account_id: str) -> Optional[str]:
        """Get stored PAT for an account."""
        return self.keyring_service.get_token(account_id)

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

    def upload_ssh_key_to_github(
        self,
        account_id: str,
        ssh_key_path: str,
        title: str = "GitHub Multi-Account Manager Key",
    ) -> Dict[str, Any]:
        """Read public key and upload directly to GitHub using account's PAT."""
        token = self.get_token(account_id)
        if not token:
            return {"success": False, "error": "Account is not logged in with a GitHub Personal Access Token."}

        pub_content = self.ssh_service.read_public_key(ssh_key_path)
        if not pub_content:
            return {"success": False, "error": f"Public key file (.pub) not found for: {ssh_key_path}"}

        return self.github_service.upload_ssh_key(token, title, pub_content)

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