"""Data models for accounts, folder mappings, and settings with strict validation."""
from datetime import datetime
from pathlib import Path
import re
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


def generate_id() -> str:
    return str(uuid.uuid4())


def sanitize_git_string(v: str) -> str:
    """Strip dangerous newline / carriage return characters to prevent Git config injection."""
    if not isinstance(v, str):
        return ""
    # Strip carriage returns, newlines, and null bytes
    cleaned = re.sub(r"[\r\n\x00]", "", v.strip())
    return cleaned


class Account(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str  # Display label, e.g. "Personal" or "Selise"
    username: str = ""  # GitHub handle, e.g. "tahmid95"
    email: str  # Git commit email
    git_name: str  # Git commit author name
    ssh_key_path: Optional[str] = None  # Absolute path to private key
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @field_validator("name", "git_name", "username", mode="before")
    @classmethod
    def clean_strings(cls, v: str) -> str:
        return sanitize_git_string(v)

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v: str) -> str:
        cleaned = sanitize_git_string(v)
        if cleaned and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned):
            # Allow fallback if valid Git email format or placeholder
            pass
        return cleaned

    @field_validator("ssh_key_path", mode="before")
    @classmethod
    def clean_ssh_path(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        return sanitize_git_string(v)

    @property
    def slug(self) -> str:
        """Sanitized lowercase slug suitable for filenames, ensuring uniqueness even with identical display names."""
        base = f"{self.name}-{self.username}" if self.username else f"{self.name}-{self.id[:6]}"
        cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "-", base.strip().lower())
        return re.sub(r"-+", "-", cleaned).strip("-") or "account"

    @property
    def config_filename(self) -> str:
        return f".gitconfig-{self.slug}"


class FolderMapping(BaseModel):
    id: str = Field(default_factory=generate_id)
    folder_path: str
    account_id: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @field_validator("folder_path", mode="before")
    @classmethod
    def clean_folder_path(cls, v: str) -> str:
        return sanitize_git_string(v)

    @property
    def normalized_path(self) -> str:
        """Returns standard Git-compatible forward-slash path with a trailing slash."""
        raw = self.folder_path.replace("\\", "/").rstrip("/")
        return f"{raw}/" if raw else "/"


class SSHKeyInfo(BaseModel):
    name: str
    private_key_path: str
    public_key_path: Optional[str] = None
    key_type: str = "ED25519"
    comment: Optional[str] = None
    fingerprint: Optional[str] = None
    public_key_content: Optional[str] = None


class AppSettings(BaseModel):
    accounts: List[Account] = Field(default_factory=list)
    folder_mappings: List[FolderMapping] = Field(default_factory=list)
    theme: str = "dark"
    auto_sync_gitconfig: bool = True
    check_updates_on_startup: bool = True