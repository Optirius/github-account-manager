from typing import Dict, Optional
import sys
import threading
import customtkinter as ctk
from PIL import Image

from github_account_manager.config import APP_NAME, APP_VERSION, ASSETS_DIR
from github_account_manager.services.manager import AccountManager
from github_account_manager.services.update_service import UpdateInfo
from github_account_manager.ui.components.update_dialog import UpdateDialog
from github_account_manager.ui.theme import (
    ACCENT_GREEN,
    ACCENT_GREEN_HOVER,
    BG_APP,
    BG_CARD,
    BG_CARD_HOVER,
    BG_SIDEBAR,
    BORDER_COLOR,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    FONT_TITLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from github_account_manager.ui.views.accounts_view import AccountsView
from github_account_manager.ui.views.apps_view import AppsView
from github_account_manager.ui.views.folders_view import FoldersView
from github_account_manager.ui.views.guide_view import GuideView
from github_account_manager.ui.views.inspector_view import InspectorView
from github_account_manager.ui.views.settings_view import SettingsView
from github_account_manager.ui.views.ssh_view import SSHView


class App(ctk.CTk):
    def __init__(self, manager: Optional[AccountManager] = None):
        super().__init__()
        self.manager = manager or AccountManager()
        self.latest_update_info: Optional[UpdateInfo] = None

        # Set appearance mode before widget creation
        ctk.set_appearance_mode(self.manager.settings.theme)
        ctk.set_default_color_theme("blue")

        # Window Configuration
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1100x720")
        self.minsize(960, 620)
        self.configure(fg_color=BG_APP)

        # Set window icon if available
        icon_path = ASSETS_DIR / "icon.ico"
        if icon_path.exists() and sys.platform == "win32":
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self._toast_timer_id = None
        self._view_cache: Dict[str, ctk.CTkFrame] = {}

        self._build_layout()
        self.show_view("accounts")

        # Background update check after app is rendered
        self.after(1500, self._check_updates_background)

        # Force window to foreground
        self.lift()
        self.attributes("-topmost", True)
        self.after_idle(lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _build_text_logo(self, logo_box):
        title_lbl = ctk.CTkLabel(
            logo_box,
            text="🐙 GitHub",
            font=FONT_TITLE,
            text_color=TEXT_PRIMARY,
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            logo_box,
            text="Multi-Account Manager",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        sub_lbl.pack(anchor="w")

    def _build_layout(self):
        # Master grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(
            self,
            width=230,
            corner_radius=0,
            fg_color=BG_SIDEBAR,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo / Title
        logo_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_box.pack(fill="x", padx=16, pady=(18, 14))

        navbar_dark = ASSETS_DIR / "navbar-logo-dark.png"
        navbar_light = ASSETS_DIR / "navbar-logo-light.png"

        if navbar_dark.exists() and navbar_light.exists():
            try:
                self._logo_img = ctk.CTkImage(
                    light_image=Image.open(navbar_light),
                    dark_image=Image.open(navbar_dark),
                    size=(185, 48),
                )
                logo_lbl = ctk.CTkLabel(
                    logo_box,
                    text="",
                    image=self._logo_img,
                )
                logo_lbl.pack(anchor="w")
            except Exception:
                self._build_text_logo(logo_box)
        else:
            self._build_text_logo(logo_box)

        # Nav Buttons
        nav_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_box.pack(fill="x", padx=10, pady=10)

        self.nav_buttons = {}

        nav_items = [
            ("guide", "📖  Guide & Quickstart"),
            ("accounts", "👤  Accounts & Profiles"),
            ("ssh", "🔑  SSH Keys"),
            ("folders", "📁  Directory Mappings"),
            ("apps", "🧩  Apps & Integrations"),
            ("inspector", "🔍  Git Inspector"),
            ("settings", "⚙️  Settings & Backups"),
        ]

        for key, text in nav_items:
            btn = ctk.CTkButton(
                nav_box,
                text=text,
                anchor="w",
                font=FONT_BODY_BOLD,
                height=40,
                fg_color="transparent",
                text_color=TEXT_SECONDARY,
                hover_color=BG_CARD_HOVER,
                command=lambda k=key: self.show_view(k),
            )
            btn.pack(fill="x", pady=3)
            self.nav_buttons[key] = btn

        # Sidebar Footer
        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=16, pady=18)

        self.footer_status = ctk.CTkLabel(
            footer,
            text=f"Profiles: {len(self.manager.settings.accounts)}\nDirectories: {len(self.manager.settings.folder_mappings)}",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            justify="left",
        )
        self.footer_status.pack(anchor="w")

        # --- Main Content Area ---
        self.content_area = ctk.CTkFrame(self, fg_color=BG_APP, corner_radius=0)
        self.content_area.grid(row=0, column=1, sticky="nsew")

        # Dedicated Toast Container (top of content area)
        self.toast_container = ctk.CTkFrame(self.content_area, fg_color="transparent", height=44)
        self.toast_container.pack(fill="x", padx=25, pady=(8, 0))
        self.toast_container.pack_propagate(False)

        # Update Available Banner (hidden by default)
        self.update_banner = ctk.CTkFrame(
            self.toast_container,
            fg_color=("#e6ffed", "#1b4729"),
            border_width=1,
            border_color=("#2da44e", "#3fb950"),
            corner_radius=6,
        )
        self.update_banner_lbl = ctk.CTkLabel(
            self.update_banner,
            text="",
            font=FONT_BODY_BOLD,
            text_color=("#1a7f37", "#7ee787"),
        )
        self.update_banner_lbl.pack(side="left", padx=16, pady=6)

        self.update_banner_btn = ctk.CTkButton(
            self.update_banner,
            text="⚡ Update Now",
            font=FONT_SMALL_BOLD,
            height=28,
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=lambda: self.open_update_dialog(self.latest_update_info),
        )
        self.update_banner_btn.pack(side="right", padx=10, pady=6)

        # Notification Toast Bar
        self.toast_bar = ctk.CTkFrame(
            self.toast_container,
            fg_color=("#ddf4ff", "#1f6feb"),
            border_width=1,
            border_color=("#54aeff", "#388bfd"),
            corner_radius=6,
        )
        self.toast_lbl = ctk.CTkLabel(
            self.toast_bar,
            text="",
            font=FONT_BODY_BOLD,
            text_color=("#0969da", "#ffffff"),
        )
        self.toast_lbl.pack(side="left", padx=16, pady=6)

        # View Host Container (holds the active view below the toast container)
        self.view_host = ctk.CTkFrame(self.content_area, fg_color="transparent", corner_radius=0)
        self.view_host.pack(fill="both", expand=True)

    def _get_or_create_view(self, view_name: str) -> Optional[ctk.CTkFrame]:
        """Lazy load views on demand to speed up initial app launch."""
        if view_name in self._view_cache:
            return self._view_cache[view_name]

        view = None
        if view_name == "guide":
            view = GuideView(self.view_host, on_navigate=self.show_view)
        elif view_name == "accounts":
            view = AccountsView(self.view_host, self.manager, on_notify=self.notify)
        elif view_name == "folders":
            view = FoldersView(
                self.view_host,
                self.manager,
                on_inspect=self.switch_to_inspect,
                on_notify=self.notify,
            )
        elif view_name == "ssh":
            view = SSHView(self.view_host, self.manager, on_notify=self.notify)
        elif view_name == "apps":
            view = AppsView(self.view_host, self.manager, on_notify=self.notify)
        elif view_name == "inspector":
            view = InspectorView(self.view_host, self.manager, on_notify=self.notify)
        elif view_name == "settings":
            view = SettingsView(
                self.view_host,
                self.manager,
                on_theme_change=self._handle_theme_change,
                on_notify=self.notify,
                on_open_update=self.open_update_dialog,
            )

        if view is not None:
            self._view_cache[view_name] = view
        return view

    def show_view(self, view_name: str):
        # Update Nav button styles
        for key, btn in self.nav_buttons.items():
            if key == view_name:
                btn.configure(fg_color=BG_CARD, text_color=TEXT_PRIMARY)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_SECONDARY)

        # Hide all currently instantiated views
        for v in self._view_cache.values():
            v.pack_forget()

        # Get or create selected view and display
        view = self._get_or_create_view(view_name)
        if view is not None:
            view.pack(fill="both", expand=True)

        self._update_footer()

    def switch_to_inspect(self, path: str):
        self.show_view("inspector")
        inspector = self._get_or_create_view("inspector")
        if isinstance(inspector, InspectorView):
            inspector.inspect_path(path)

    def _handle_theme_change(self, theme: str):
        ctk.set_appearance_mode(theme)

    def _update_footer(self):
        self.footer_status.configure(
            text=f"Profiles: {len(self.manager.settings.accounts)}\nDirectories: {len(self.manager.settings.folder_mappings)}"
        )

    def notify(self, title: str, message: str, is_error: bool = False):
        """Display a safe, crash-proof toast notification."""
        try:
            if is_error:
                self.toast_bar.configure(
                    fg_color=("#ffebe9", "#da3633"),
                    border_color=("#ff8182", "#f85149"),
                )
                self.toast_lbl.configure(
                    text=f"✗  {title}: {message}",
                    text_color=("#cf222e", "#ffffff"),
                )
            else:
                self.toast_bar.configure(
                    fg_color=("#ddf4ff", "#1f6feb"),
                    border_color=("#54aeff", "#388bfd"),
                )
                self.toast_lbl.configure(
                    text=f"✓  {title}: {message}",
                    text_color=("#0969da", "#ffffff"),
                )

            self.toast_bar.pack(fill="both", expand=True)

            if self._toast_timer_id is not None:
                self.after_cancel(self._toast_timer_id)

            def hide():
                try:
                    self.toast_bar.pack_forget()
                except Exception:
                    pass

            self._toast_timer_id = self.after(3500, hide)
            self._update_footer()
        except Exception:
            pass

    def _check_updates_background(self):
        """Perform a quiet update check in the background."""
        if not getattr(self.manager.settings, "check_updates_on_startup", True):
            return

        def task():
            try:
                info = self.manager.update_service.check_for_updates()
                if info and info.is_update_available:
                    self.latest_update_info = info
                    self.after(0, lambda: self._show_update_banner(info))
            except Exception:
                pass

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _show_update_banner(self, info: UpdateInfo):
        """Display non-intrusive update banner at the top of the content area."""
        try:
            self.update_banner_lbl.configure(
                text=f"🎉  New Version {info.latest_version} Available! (Current: {info.current_version})"
            )
            self.update_banner.pack(fill="both", expand=True)
        except Exception:
            pass

    def open_update_dialog(self, info: Optional[UpdateInfo] = None):
        """Open the interactive update dialog, or focus existing instance without locking views."""
        if hasattr(self, "_active_update_dialog") and self._active_update_dialog is not None:
            try:
                if self._active_update_dialog.winfo_exists():
                    self._active_update_dialog.lift()
                    self._active_update_dialog.focus_force()
                    return
            except Exception:
                self._active_update_dialog = None

        target_info = info or self.latest_update_info
        if target_info and target_info.is_update_available:
            self._active_update_dialog = UpdateDialog(
                self,
                self.manager.update_service,
                target_info,
                on_notify=self.notify,
                on_close=lambda: setattr(self, "_active_update_dialog", None),
            )
        else:
            # Check immediately
            def task():
                return self.manager.update_service.check_for_updates()

            def on_done(fetched_info: Optional[UpdateInfo]):
                if fetched_info is None:
                    self.notify("Update Check", "Could not check for updates (offline or rate limit).", is_error=True)
                elif fetched_info.is_update_available:
                    self.latest_update_info = fetched_info
                    self._show_update_banner(fetched_info)
                    if not (hasattr(self, "_active_update_dialog") and self._active_update_dialog and self._active_update_dialog.winfo_exists()):
                        self._active_update_dialog = UpdateDialog(
                            self,
                            self.manager.update_service,
                            fetched_info,
                            on_notify=self.notify,
                            on_close=lambda: setattr(self, "_active_update_dialog", None),
                        )
                    else:
                        self._active_update_dialog.lift()
                        self._active_update_dialog.focus_force()
                else:
                    self.notify("Up to Date", f"You are running the latest version ({fetched_info.current_version}).")

            def worker():
                res = task()
                self.after(0, lambda: on_done(res))

            threading.Thread(target=worker, daemon=True).start()

    def report_callback_exception(self, exc, val, tb):
        """Catch all Tkinter callback exceptions to log them and prevent silent window closure."""
        import logging
        import traceback
        err = "".join(traceback.format_exception(exc, val, tb))
        logging.getLogger("ui").error(f"Tkinter callback exception:\n{err}")
        try:
            self.notify("UI Notice", str(val), is_error=True)
        except Exception:
            pass