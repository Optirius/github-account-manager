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


ORIGINAL_STDOUT = sys.__stdout__ or sys.stdout
ORIGINAL_STDERR = sys.__stderr__ or sys.stderr


class LogStream:
    def __init__(self, prefix, original_stream=None):
        self.prefix = prefix
        self.original_stream = original_stream

    def write(self, text):
        cleaned = text.strip()
        if cleaned:
            log_debug(f"[{self.prefix}] {cleaned}")
        if self.original_stream and getattr(self.original_stream, "write", None):
            try:
                self.original_stream.write(text)
                self.original_stream.flush()
            except Exception:
                pass

    def flush(self):
        if self.original_stream and getattr(self.original_stream, "flush", None):
            try:
                self.original_stream.flush()
            except Exception:
                pass


sys.stdout = LogStream("STDOUT", ORIGINAL_STDOUT)
sys.stderr = LogStream("STDERR", ORIGINAL_STDERR)


def check_tkinter_or_exit():
    """Verify Tkinter is installed before launching GUI components."""
    try:
        import tkinter
    except ModuleNotFoundError:
        msg = (
            "\n"
            "======================================================================\n"
            "[ERROR] Python Tkinter is not installed on this system!\n"
            "----------------------------------------------------------------------\n"
            "The application GUI requires Tkinter to run.\n"
            "Please install Tkinter using your Linux distribution's package manager:\n\n"
            "  • Ubuntu / Debian / Linux Mint:  sudo apt install -y python3-tk\n"
            "  • Fedora / RHEL / CentOS:       sudo dnf install -y python3-tkinter\n"
            "  • Arch Linux / Manjaro:         sudo pacman -S tk\n"
            "  • openSUSE:                      sudo zypper install python3-tk\n\n"
            "After installing, please relaunch the application.\n"
            "======================================================================\n"
        )
        log_debug(msg)
        if ORIGINAL_STDERR and getattr(ORIGINAL_STDERR, "write", None):
            try:
                ORIGINAL_STDERR.write(msg)
                ORIGINAL_STDERR.flush()
            except Exception:
                pass
        sys.exit(1)


def global_excepthook(exc_type, exc_val, exc_tb):
    err = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
    log_debug(f"[CRITICAL_UNCAUGHT_EXCEPTION]\n{err}")

    # Output to original stderr so terminal users see the error
    if ORIGINAL_STDERR and getattr(ORIGINAL_STDERR, "write", None):
        try:
            ORIGINAL_STDERR.write(f"\n[CRITICAL ERROR] {exc_val}\n{err}\n")
            ORIGINAL_STDERR.flush()
        except Exception:
            pass

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

    # Pre-flight check for Tkinter
    check_tkinter_or_exit()

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
        sys.exit(1)