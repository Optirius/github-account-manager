"""Launcher script for local development and PyInstaller entry with same-directory debug logging."""
import datetime
import multiprocessing
import os
from pathlib import Path
import sys
import threading
import traceback

# 1. Determine execution directory (same directory as .exe or script)
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).resolve().parent

LOG_FILE = APP_DIR / "debug.log"


def log_debug(msg: str):
    """Write message immediately to debug.log next to the executable."""
    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"[{now_str}] {msg}\n")
            f.flush()
    except Exception:
        pass


# Start log session
log_debug(f"==================================================")
log_debug(f"=== Process Started (PID: {os.getpid()}) ===")
log_debug(f"Executable: {sys.executable}")
log_debug(f"Working Directory: {os.getcwd()}")
log_debug(f"App Directory: {APP_DIR}")
log_debug(f"Frozen: {getattr(sys, 'frozen', False)}")
log_debug(f"Python: {sys.version}")
log_debug(f"Arguments: {sys.argv}")


class LogStream:
    def __init__(self, prefix):
        self.prefix = prefix

    def write(self, text):
        cleaned = text.strip()
        if cleaned:
            log_debug(f"[{self.prefix}] {cleaned}")

    def flush(self):
        pass


sys.stdout = LogStream("STDOUT")
sys.stderr = LogStream("STDERR")


def global_excepthook(exc_type, exc_val, exc_tb):
    err = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
    log_debug(f"[CRITICAL_UNCAUGHT_EXCEPTION]\n{err}")
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "GitHub Multi-Account Manager Error",
            f"An error occurred and has been logged to:\n{LOG_FILE}\n\nError: {exc_val}",
        )
        root.destroy()
    except Exception as e:
        log_debug(f"Failed to display messagebox: {e}")


def thread_excepthook(args):
    err = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    log_debug(f"[THREAD_EXCEPTION]\n{err}")


sys.excepthook = global_excepthook
threading.excepthook = thread_excepthook

if __name__ == "__main__":
    log_debug("Calling multiprocessing.freeze_support()...")
    multiprocessing.freeze_support()
    log_debug("freeze_support() passed. Importing github_account_manager.main...")
    try:
        from github_account_manager.main import main

        log_debug("Module imported successfully. Executing main()...")
        main(log_fn=log_debug)
        log_debug("main() completed cleanly.")
    except Exception as e:
        err = traceback.format_exc()
        log_debug(f"[FATAL_STARTUP_ERROR]\n{err}")
        global_excepthook(*sys.exc_info())