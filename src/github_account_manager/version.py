"""Centralized application version management for GitHub Multi-Account Manager.

This module is the single source of truth for the application version.
"""
from pathlib import Path
import os
import re
import subprocess
import sys
from typing import Optional

# Canonical application version
__version__ = "0.2.0"


def _find_version_file() -> Optional[Path]:
    """Locate the root version.txt file in dev checkout or frozen bundle."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            cand = Path(meipass) / "version.txt"
            if cand.exists():
                return cand
        cand_exe = Path(sys.executable).parent / "version.txt"
        if cand_exe.exists():
            return cand_exe
    else:
        cur = Path(__file__).resolve().parent
        for _ in range(4):
            cand = cur / "version.txt"
            if cand.exists():
                return cand
            cur = cur.parent
    return None


def get_version() -> str:
    """
    Get the application version string.

    Resolution order:
    1. APP_VERSION_OVERRIDE environment variable (if set by build runner)
    2. Root version.txt file
    3. Canonical __version__ defined in this file (fallback)
    """
    env_ver = os.getenv("APP_VERSION_OVERRIDE")
    if env_ver:
        return env_ver.strip().lstrip("v")

    v_file = _find_version_file()
    if v_file:
        try:
            val = v_file.read_text(encoding="utf-8").strip().lstrip("v")
            if val:
                return val
        except Exception:
            pass

    return __version__.strip().lstrip("v") if __version__ else "0.2.0"


def set_version(new_version: str) -> str:
    """
    Update the canonical version in version.txt and in this file.

    Args:
        new_version: Version string, e.g. "0.2.0" or "v0.2.0"
    Returns:
        Cleaned version string without leading 'v'.
    """
    global __version__
    clean_ver = new_version.strip().lstrip("v")

    # 1. Update version.txt
    v_file = _find_version_file()
    if not v_file:
        v_file = Path(__file__).resolve().parent.parent.parent / "version.txt"
    try:
        v_file.write_text(f"{clean_ver}\n", encoding="utf-8")
    except Exception:
        pass

    # 2. Update __version__ in this file for static tools (hatchling, importlib)
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
