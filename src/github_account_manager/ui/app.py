"""Main Application window with modular view switching, lazy view loading, and custom notifications."""
from typing import Dict, Optional
import customtkinter as ctk

from github_account_manager.config import APP_NAME, APP_VERSION
from github_account_manager.services.manager import AccountManager
from github_account_manager.ui.theme import (
    BG_APP,
    BG_CARD,
    BG_CARD_HOVER,
    BG_SIDEBAR,
    BORDER_COLOR,
    FONT_BODY_BOLD,
    FONT_SMALL,
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

        # Set appearance mode before widget creation
        ctk.set_appearance_mode(self.manager.settings.theme)
        ctk.set_default_color_theme("blue")

        # Window Configuration
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1100x720")
        self.minsize(960, 620)
        self.configure(fg_color=BG_APP)

        self._toast_timer_id = None
        self._view_cache: Dict[str, ctk.CTkFrame] = {}

        self._build_layout()
        self.show_view("accounts")

        # Force window to foreground
        self.lift()
        self.attributes("-topmost", True)
        self.after_idle(lambda: self.attributes("-topmost", False))
        self.focus_force()

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
        logo_box.pack(fill="x", padx=18, pady=(22, 16))

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

        # Nav Buttons
        nav_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_box.pack(fill="x", padx=10, pady=10)

        self.nav_buttons = {}

        nav_items = [
            ("guide", "📖  Guide & Quickstart"),
            ("accounts", "👤  Accounts & Profiles"),
            ("folders", "📁  Directory Mappings"),
            ("ssh", "🔑  SSH Keys"),
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