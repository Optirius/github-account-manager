"""Common cross-platform subprocess and helper utilities."""
import subprocess
import sys
from typing import Any, Dict


def get_no_window_kwargs() -> Dict[str, Any]:
    """Returns kwargs for subprocess to prevent any console window popup on Windows."""
    kwargs: Dict[str, Any] = {}
    if sys.platform == "win32":
        # 0x08000000 = CREATE_NO_WINDOW
        kwargs["creationflags"] = 0x08000000
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        kwargs["startupinfo"] = startupinfo
    return kwargs


def safe_subprocess_run(cmd, **kwargs) -> subprocess.CompletedProcess:
    """Execute a subprocess command with complete window suppression on Windows."""
    no_win = get_no_window_kwargs()
    for k, v in no_win.items():
        if k not in kwargs:
            kwargs[k] = v
    return subprocess.run(cmd, **kwargs)