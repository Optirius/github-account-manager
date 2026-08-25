"""Async task execution helper for CustomTkinter with UI button loaders and error modal popups."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import threading
import traceback
from typing import Any, Callable, Optional
import customtkinter as ctk

logger = logging.getLogger(__name__)

# Dedicated thread pool for async background operations
_EXECUTOR = ThreadPoolExecutor(max_workers=6, thread_name_prefix="AsyncWorker")


def run_async(
    widget: ctk.CTkBaseClass,
    task_fn: Callable[[], Any],
    on_success: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
    loading_btn: Optional[ctk.CTkButton] = None,
    loading_text: str = "⏳ Processing...",
    show_error_dialog: bool = True,
    error_title: str = "Operation Failed",
):
    """
    Execute a task in a background worker thread without blocking the GUI event loop.
    Handles button loading state, safe UI callback marshaling, and error dialog presentation.
    """
    original_text = ""
    original_state = "normal"
    original_fg = None

    if loading_btn and hasattr(loading_btn, "cget"):
        try:
            original_text = loading_btn.cget("text")
            original_state = loading_btn.cget("state")
            original_fg = loading_btn.cget("fg_color")
            loading_btn.configure(text=loading_text, state="disabled")
        except Exception:
            pass

    def worker():
        try:
            result = task_fn()
            
            def success_cb():
                _restore_btn()
                if on_success:
                    on_success(result)

            widget.after(0, success_cb)

        except Exception as exc:
            err_details = traceback.format_exc()
            logger.error(f"Async error in {task_fn}: {err_details}")

            def error_cb():
                _restore_btn()
                if on_error:
                    on_error(exc)
                if show_error_dialog:
                    from github_account_manager.ui.components.dialogs import ErrorModalDialog
                    ErrorModalDialog(
                        widget.winfo_toplevel(),
                        title=error_title,
                        message=str(exc),
                        details=err_details,
                    )

            widget.after(0, error_cb)

    def _restore_btn():
        if loading_btn and original_text:
            try:
                loading_btn.configure(text=original_text, state=original_state)
            except Exception:
                pass

    _EXECUTOR.submit(worker)