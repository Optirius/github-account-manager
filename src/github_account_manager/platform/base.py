"""Abstract base class defining the PlatformAdapter interface for OS-specific operations."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class PlatformAdapter(ABC):
    """Abstract interface for operating system specific paths, tools, and credentials."""

    @property
    @abstractmethod
    def os_name(self) -> str:
        """Name of the operating system ('windows', 'macos', 'linux')."""
        pass

    @abstractmethod
    def get_ide_settings_paths(self, ide_id: str) -> List[Path]:
        """Return candidate configuration / settings.json file paths for a given IDE."""
        pass

    @abstractmethod
    def detect_installed_apps(self) -> List[Dict[str, Any]]:
        """Discover installed Git GUI clients and code editors on the system."""
        pass

    @abstractmethod
    def list_git_credentials(self) -> List[Dict[str, Any]]:
        """List cached global Git credentials from the OS credential store."""
        pass

    @abstractmethod
    def delete_git_credential(self, target: str) -> bool:
        """Delete a conflicting Git credential entry from the OS credential store."""
        pass

    @abstractmethod
    def get_default_ssh_dir(self) -> Path:
        """Return default path to ~/.ssh."""
        pass

    @abstractmethod
    def get_default_gitconfig_path(self) -> Path:
        """Return default path to ~/.gitconfig."""
        pass

    @abstractmethod
    def get_default_data_dir(self) -> Path:
        """Return default application data storage directory."""
        pass

    @abstractmethod
    def get_system_font_family(self) -> str:
        """Return preferred native system UI font family for this OS."""
        pass

    def get_ide_github_accounts(self) -> List[Dict[str, Any]]:
        """Extract GitHub accounts configured inside external IDEs (such as JetBrains Rider / IntelliJ)."""
        return []

    def discover_editor_configs(self) -> List[Dict[str, Any]]:
        """Dynamically discover any installed code editor / IDE configuration directories containing settings.json."""
        return []