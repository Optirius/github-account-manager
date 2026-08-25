"""Platform module providing operating system specific adapters for Windows, macOS, and Linux."""
import sys
from typing import Optional

from github_account_manager.platform.base import PlatformAdapter
from github_account_manager.platform.windows import WindowsPlatformAdapter
from github_account_manager.platform.macos import MacOSPlatformAdapter
from github_account_manager.platform.linux import LinuxPlatformAdapter

__all__ = [
    "PlatformAdapter",
    "WindowsPlatformAdapter",
    "MacOSPlatformAdapter",
    "LinuxPlatformAdapter",
    "get_platform_adapter",
]

_CURRENT_ADAPTER: Optional[PlatformAdapter] = None


def get_platform_adapter(os_name: Optional[str] = None) -> PlatformAdapter:
    """Return the singleton or customized platform adapter for the target OS."""
    target_os = (os_name or sys.platform).lower()

    if target_os.startswith("win") or target_os in ("windows", "nt"):
        return WindowsPlatformAdapter()
    elif target_os.startswith("darwin") or "mac" in target_os or "osx" in target_os:
        return MacOSPlatformAdapter()
    elif target_os.startswith("linux"):
        return LinuxPlatformAdapter()

    # Fallback to Linux adapter for other POSIX environments
    return LinuxPlatformAdapter()