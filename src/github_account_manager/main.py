"""Application entry point with freeze_support, safe streams, and crash logging."""
import io
import logging
from logging.handlers import RotatingFileHandler
import multiprocessing
import os
from pathlib import Path
import sys
import threading
import traceback

from github_account_manager.config import DATA_DIR, APP_NAME, APP_VERSION


def setup_logging_and_streams(log_fn=None):
    """Ensure logs are persisted to app.log and stdout/stderr are safe for windowed/GUI execution."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_file = DATA_DIR / "app.log"

    # Rotating file handler (max 2MB, up to 3 backups)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [file_handler]

    # Safe redirect for sys.stdout / sys.stderr when running in windowed mode
    class SafeStreamWriter:
        def __init__(self, level):
            self.level = level
            self.logger = logging.getLogger("sys")

        def write(self, message):
            msg = message.strip()
            if msg:
                self.logger.log(self.level, msg)
                if log_fn:
                    log_fn(f"[STREAM_{self.level}] {msg}")

        def flush(self):
            pass

    if sys.stdout is None or not hasattr(sys.stdout, "write"):
        sys.stdout = SafeStreamWriter(logging.INFO)
    if sys.stderr is None or not hasattr(sys.stderr, "write"):
        sys.stderr = SafeStreamWriter(logging.ERROR)

    def global_excepthook(exc_type, exc_val, exc_tb):
        err = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        root_logger.critical(f"Uncaught exception:\n{err}")
        if log_fn:
            log_fn(f"[UNCAUGHT_EXCEPTION]\n{err}")

        orig_err = sys.__stderr__ or sys.stderr
        if orig_err and getattr(orig_err, "write", None):
            try:
                orig_err.write(f"\n[CRITICAL ERROR] {exc_val}\n{err}\n")
                orig_err.flush()
            except Exception:
                pass

        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                f"{APP_NAME} Error",
                f"An unexpected error occurred.\n\nDetails:\n{exc_val}",
            )
            root.destroy()
        except Exception:
            pass

    def thread_excepthook(args):
        err = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        root_logger.error(f"Uncaught background thread exception:\n{err}")
        if log_fn:
            log_fn(f"[THREAD_EXCEPTION]\n{err}")

    sys.excepthook = global_excepthook
    threading.excepthook = thread_excepthook


def main(log_fn=None):
    # 1. Critical for PyInstaller on Windows: prevent child process fork bomb
    multiprocessing.freeze_support()

    # 2. Setup logging and crash handlers
    setup_logging_and_streams(log_fn=log_fn)

    logger = logging.getLogger(__name__)
    msg = f"Starting {APP_NAME} v{APP_VERSION} (Python {sys.version.split()[0]} on {sys.platform})"
    logger.info(msg)
    if log_fn:
        log_fn(msg)

    # 3. Handle CLI information arguments (help, version)
    if "--version" in sys.argv:
        print(f"{APP_NAME} v{APP_VERSION}")
        sys.exit(0)

    if "--help" in sys.argv or "-h" in sys.argv:
        print(f"{APP_NAME} v{APP_VERSION}")
        print("Cross-platform desktop GitHub multi-account and SSH profile manager.")
        print("\nUsage:")
        print("  github-account-manager [options]")
        print("\nOptions:")
        print("  --version          Display application version and exit")
        print("  --smoke-test       Verify UI initialization and exit without entering mainloop")
        print("  -h, --help         Show this help message and exit")
        sys.exit(0)

    # 4. Pre-flight check for Tkinter availability
    try:
        import tkinter
    except ModuleNotFoundError:
        tk_err = (
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
        logger.critical(tk_err)
        if log_fn:
            log_fn(tk_err)
        orig_err = sys.__stderr__ or sys.stderr
        if orig_err and getattr(orig_err, "write", None):
            try:
                orig_err.write(tk_err)
                orig_err.flush()
            except Exception:
                pass
        sys.exit(1)

    # 5. Handle smoke test (requires Tkinter)
    if "--smoke-test" in sys.argv:
        if log_fn:
            log_fn("Running smoke test...")
        from github_account_manager.ui.app import App
        app = App()
        app.update()
        app.destroy()
        smoke_msg = f"[OK] Smoke test passed for {APP_NAME} v{APP_VERSION}"
        if log_fn:
            log_fn(smoke_msg)
        print(smoke_msg)
        sys.exit(0)

    try:
        if log_fn:
            log_fn("Importing App class...")
        from github_account_manager.ui.app import App
        if log_fn:
            log_fn("Instantiating App()...")
        app = App()
        if log_fn:
            log_fn("Entering app.mainloop()...")
        app.mainloop()
        if log_fn:
            log_fn("mainloop() exited.")
    except Exception as e:
        err = traceback.format_exc()
        logger.critical(f"Fatal error in main application loop:\n{err}")
        if log_fn:
            log_fn(f"[FATAL_MAIN_LOOP_ERROR]\n{err}")
        raise


if __name__ == "__main__":
    main()