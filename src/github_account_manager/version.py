"""Centralized application version management for GitHub Multi-Account Manager.

This module is the single source of truth for the application version.
"""
from pathlib import Path
import os
import re
import subprocess
import sys

# Canonical application version
__version__ = "0.1.29"


def get_version() -> str:
    """
    Get the application version string.

    Resolution order:
    1. APP_VERSION_OVERRIDE environment variable (set by CI/CD or build runner)
    2. Canonical __version__ defined in this file
    3. Git commit count fallback (if running in active git worktree and __version__ is default 0.1.0)
    """
    env_ver = os.getenv("APP_VERSION_OVERRIDE")
    if env_ver:
        return env_ver.strip().lstrip("v")

    if __version__ and __version__ != "0.1.0":
        return __version__.strip().lstrip("v")

    # Fallback to git commit count if unversioned dev checkout
    try:
        kw = {"creationflags": 0x08000000} if sys.platform == "win32" else {}
        res = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            **kw,
        )
        if res.returncode == 0 and res.stdout.strip().isdigit():
            return f"0.1.{res.stdout.strip()}"
    except Exception:
        pass

    return __version__ or "0.1.0"


def set_version(new_version: str) -> str:
    """
    Update the canonical __version__ in this file.

    Args:
        new_version: Version string, e.g. "0.1.29" or "v0.1.29"
    Returns:
        Cleaned version string without leading 'v'.
    """
    global __version__
    clean_ver = new_version.strip().lstrip("v")
    version_file = Path(__file__).resolve()
    content = version_file.read_text(encoding="utf-8")

    new_content, count = re.subn(
        r"^__version__\s*=\s*[\"'][^\"']+[\"']",
        f'__version__ = "{clean_ver}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if count == 0:
        raise ValueError("Could not find __version__ definition to update")
    version_file.write_text(new_content, encoding="utf-8")

    # Invalidate pycache & update in-memory global
    __version__ = clean_ver
    try:
        pycache = version_file.parent / "__pycache__"
        if pycache.exists():
            for pyc in pycache.glob("version*.pyc"):
                pyc.unlink(missing_ok=True)
        import importlib
        importlib.invalidate_caches()
    except Exception:
        pass

    return clean_ver
