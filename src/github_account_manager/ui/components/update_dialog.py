"""Interactive Modal Dialog for Application Updates with Real-Time Progress."""
import threading
from typing import Callable, Optional
import customtkinter as ctk

from github_account_manager.services.update_service import UpdateInfo, UpdateService
from github_account_manager.ui.theme import (
    ACCENT_GREEN,
    ACCENT_GREEN_HOVER,
    BG_CARD,
    BG_INSET,
    BORDER_COLOR,
    BTN_SECONDARY_BG,
    BTN_SECONDARY_HOVER,
    BTN_SECONDARY_TEXT,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_HEADING,
    FONT_MONO_SMALL,
    FONT_SMALL,
    FONT_SUBHEADING,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class UpdateDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        update_service: UpdateService,
        update_info: UpdateInfo,
        on_notify: Optional[Callable[[str, str], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.update_service = update_service
        self.update_info = update_info
        self.on_notify = on_notify
        self.on_close = on_close

        self.title("Software Update Available")
        self.geometry("540x480")
        self.resizable(False, False)
        self.configure(fg_color=BG_CARD)

        # Window relationship without blocking grab
        self.transient(parent)
        self.lift()
        self.focus_force()

        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._is_updating = False
        self._build_ui()

        # Center on parent
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() - 540) // 2
            y = parent.winfo_y() + (parent.winfo_height() - 480) // 2
            self.geometry(f"+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

    def destroy(self):
        try:
            if hasattr(self, "on_close") and self.on_close:
                self.on_close()
        except Exception:
            pass
        super().destroy()

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=20)

        # Header
        top_row = ctk.CTkFrame(main, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            top_row,
            text="🎉  New Update Available!",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        # Version Pill
        ver_box = ctk.CTkFrame(main, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
        ver_box.pack(fill="x", pady=(0, 12))

        ver_content = ctk.CTkFrame(ver_box, fg_color="transparent")
        ver_content.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(
            ver_content,
            text=f"Current: {self.update_info.current_version}  ➔  Latest: {self.update_info.latest_version}",
            font=FONT_BODY_BOLD,
            text_color=ACCENT_GREEN,
        ).pack(side="left")

        if self.update_info.published_at:
            ctk.CTkLabel(
                ver_content,
                text=f"Released: {self.update_info.published_at}",
                font=FONT_SMALL,
                text_color=TEXT_MUTED,
            ).pack(side="right")

        # Release Notes / Changelog
        ctk.CTkLabel(
            main,
            text="What's New in This Release:",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 4))

        notes_box = ctk.CTkTextbox(
            main,
            height=160,
            font=FONT_MONO_SMALL,
            fg_color=BG_INSET,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
        )
        notes_box.pack(fill="x", pady=(0, 14))
        notes_box.insert("1.0", self.update_info.release_notes.strip())
        notes_box.configure(state="disabled")

        # Progress / Status Area
        self.progress_bar = ctk.CTkProgressBar(main, height=10)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 6))

        self.status_lbl = ctk.CTkLabel(
            main,
            text=f"Asset: {self.update_info.asset_name or 'Ready to download'}",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        self.status_lbl.pack(anchor="w", pady=(0, 14))

        # Action Buttons
        btn_row = ctk.CTkFrame(main, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        self.cancel_btn = ctk.CTkButton(
            btn_row,
            text="Later",
            font=FONT_BODY,
            width=100,
            height=34,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self.destroy,
        )
        self.cancel_btn.pack(side="right", padx=(8, 0))

        self.update_btn = ctk.CTkButton(
            btn_row,
            text=f"⚡ Update & Restart to {self.update_info.latest_version}",
            font=FONT_BODY_BOLD,
            height=34,
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=self._start_update,
        )
        self.update_btn.pack(side="right")

    def _start_update(self):
        if self._is_updating:
            return
        self._is_updating = True

        self.update_btn.configure(state="disabled", text="⏳ Updating...")
        self.cancel_btn.configure(state="disabled")

        def run_update_thread():
            def progress(pct: float, msg: str):
                self.after(0, lambda: self._update_progress(pct, msg))

            try:
                # 1. Download and extract
                new_binary = self.update_service.download_and_extract_asset(
                    self.update_info,
                    progress_callback=progress,
                )

                self.after(0, lambda: self._update_progress(1.0, "Launching updater & restarting..."))

                # 2. Apply and restart
                self.after(500, lambda: self.update_service.apply_and_restart(new_binary))

            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._handle_error(err_msg))

        thread = threading.Thread(target=run_update_thread, daemon=True)
        thread.start()

    def _update_progress(self, pct: float, msg: str):
        self.progress_bar.set(pct)
        self.status_lbl.configure(text=msg)

    def _handle_error(self, err_msg: str):
        self._is_updating = False
        self.update_btn.configure(state="normal", text="Retry Update")
        self.cancel_btn.configure(state="normal")
        self.status_lbl.configure(text=f"❌ Update failed: {err_msg}", text_color="#cf222e")
        if self.on_notify:
            self.on_notify("Update Error", err_msg, is_error=True)
