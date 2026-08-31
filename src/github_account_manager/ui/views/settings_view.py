"""Settings view for configuring theme, viewing global gitconfig, and managing backups."""
from pathlib import Path
import shutil
from typing import Callable, Optional
import customtkinter as ctk

from github_account_manager.config import APP_VERSION, BACKUP_DIR, DEFAULT_GITCONFIG
from github_account_manager.services.manager import AccountManager
from github_account_manager.services.update_service import UpdateInfo
from github_account_manager.ui.async_runner import run_async
from github_account_manager.ui.components.info_banner import InfoBanner
from github_account_manager.ui.theme import (
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
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
    FONT_SMALL_BOLD,
    FONT_SUBHEADING,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class SettingsView(ctk.CTkFrame):
    def __init__(
        self,
        master,
        manager: AccountManager,
        on_theme_change: Callable[[str], None],
        on_notify: Callable[[str, str], None],
        on_open_update: Optional[Callable[[UpdateInfo], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.manager = manager
        self.on_theme_change = on_theme_change
        self.on_notify = on_notify
        self.on_open_update = on_open_update

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(22, 10))

        ctk.CTkLabel(
            header,
            text="Settings & Git Config Manager",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Manage application appearance, automatic synchronization, and Git configuration backups.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(3, 0))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=25, pady=(10, 20))

        # Contextual explanation banner
        InfoBanner(
            scroll,
            title="How Git Config Synchronization & Backups Work",
            what_it_does="Manages automatic ~/.gitconfig writing, visual themes, and safe snapshot backups.",
            why_needed="Ensures your Git settings stay in sync with zero risk of corruption—you can rollback anytime with 1-click snapshots.",
            how_it_works="Performs atomic file replacement and stores the last 15 versions in ~/.github_account_manager/backups/.",
            icon="⚙️",
        ).pack(fill="x", pady=(0, 15))

        # App Preferences Card
        pref_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        pref_card.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(pref_card, text="App Preferences", font=FONT_SUBHEADING, text_color=TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(14, 8))

        # Theme option
        theme_row = ctk.CTkFrame(pref_card, fg_color="transparent")
        theme_row.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(theme_row, text="UI Theme:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, width=170, anchor="w").pack(side="left")
        self.theme_combo = ctk.CTkComboBox(
            theme_row,
            values=["dark", "light", "system"],
            command=self._on_theme_selected,
            height=34,
            font=FONT_BODY,
        )
        self.theme_combo.set(self.manager.settings.theme)
        self.theme_combo.pack(side="left")

        # Auto-sync switch
        sync_row = ctk.CTkFrame(pref_card, fg_color="transparent")
        sync_row.pack(fill="x", padx=16, pady=(8, 16))
        ctk.CTkLabel(sync_row, text="Auto-sync Gitconfig:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, width=170, anchor="w").pack(side="left")
        self.sync_switch = ctk.CTkSwitch(
            sync_row,
            text="Automatically write ~/.gitconfig on changes",
            font=FONT_BODY,
            command=self._on_sync_toggled,
        )
        if self.manager.settings.auto_sync_gitconfig:
            self.sync_switch.select()
        else:
            self.sync_switch.deselect()
        self.sync_switch.pack(side="left")

        # Software Updates & Releases Card
        update_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        update_card.pack(fill="x", pady=(0, 15))

        up_head = ctk.CTkFrame(update_card, fg_color="transparent")
        up_head.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(up_head, text="Software Updates & Releases", font=FONT_SUBHEADING, text_color=TEXT_PRIMARY).pack(side="left")

        # Startup check switch
        startup_row = ctk.CTkFrame(update_card, fg_color="transparent")
        startup_row.pack(fill="x", padx=16, pady=(6, 8))
        ctk.CTkLabel(startup_row, text="Startup Auto-Check:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, width=170, anchor="w").pack(side="left")
        self.startup_check_switch = ctk.CTkSwitch(
            startup_row,
            text="Check for latest version on application startup",
            font=FONT_BODY,
            command=self._on_startup_check_toggled,
        )
        if getattr(self.manager.settings, "check_updates_on_startup", True):
            self.startup_check_switch.select()
        else:
            self.startup_check_switch.deselect()
        self.startup_check_switch.pack(side="left")

        # Current version & Manual check row
        ver_row = ctk.CTkFrame(update_card, fg_color="transparent")
        ver_row.pack(fill="x", padx=16, pady=(4, 14))

        self.ver_status_lbl = ctk.CTkLabel(
            ver_row,
            text=f"Installed Version: v{APP_VERSION}",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        )
        self.ver_status_lbl.pack(side="left")

        self.btn_box = ctk.CTkFrame(ver_row, fg_color="transparent")
        self.btn_box.pack(side="right")

        self.install_update_btn = ctk.CTkButton(
            self.btn_box,
            text="⚡ View & Install",
            width=135,
            height=30,
            font=FONT_SMALL_BOLD,
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=self._install_detected_update,
        )

        self.check_update_btn = ctk.CTkButton(
            self.btn_box,
            text="🔄 Check for Updates",
            width=160,
            height=30,
            font=FONT_SMALL_BOLD,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self._check_for_updates_action,
        )
        self.check_update_btn.pack(side="right")

        # Global Gitconfig Live View
        git_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        git_card.pack(fill="x", pady=(0, 15))

        git_head = ctk.CTkFrame(git_card, fg_color="transparent")
        git_head.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(git_head, text=f"Global Git Config ({DEFAULT_GITCONFIG})", font=FONT_SUBHEADING, text_color=TEXT_PRIMARY).pack(side="left")

        reload_btn = ctk.CTkButton(
            git_head,
            text="🔄 Refresh View",
            width=115,
            height=30,
            font=FONT_SMALL,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self._reload_gitconfig_view,
        )
        reload_btn.pack(side="right")

        self.gitconfig_text = ctk.CTkTextbox(
            git_card,
            height=180,
            font=FONT_MONO_SMALL,
            fg_color=BG_INSET,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
        )
        self.gitconfig_text.pack(fill="x", padx=16, pady=(0, 14))
        self._reload_gitconfig_view()

        # Backups Card
        backup_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        backup_card.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(backup_card, text="Git Config Backups", font=FONT_SUBHEADING, text_color=TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            backup_card,
            text=f"Automatic snapshots stored in: {BACKUP_DIR}",
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=16, pady=(0, 10))

        self.backups_box = ctk.CTkFrame(backup_card, fg_color="transparent")
        self.backups_box.pack(fill="x", padx=16, pady=(0, 14))
        self._render_backups()

    def _on_theme_selected(self, choice: str):
        self.manager.settings.theme = choice
        self.manager.save_settings()
        self.on_theme_change(choice)

    def _on_sync_toggled(self):
        self.manager.settings.auto_sync_gitconfig = bool(self.sync_switch.get())
        self.manager.save_settings()

    def _reload_gitconfig_view(self):
        content = self.manager.git_service.get_gitconfig_content()
        self.gitconfig_text.delete("1.0", "end")
        self.gitconfig_text.insert("1.0", content or "(No .gitconfig file found)")

    def _render_backups(self):
        for w in self.backups_box.winfo_children():
            w.destroy()

        backups = sorted(list(BACKUP_DIR.glob("*.bak")), reverse=True)[:5]
        if not backups:
            ctk.CTkLabel(self.backups_box, text="No backups created yet.", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")
            return

        for b in backups:
            row = ctk.CTkFrame(self.backups_box, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(row, text=f"💾 {b.name}", font=FONT_MONO_SMALL, text_color=TEXT_PRIMARY).pack(side="left", padx=10, pady=6)

            ctk.CTkButton(
                row,
                text="Restore",
                width=75,
                height=26,
                font=FONT_SMALL,
                fg_color=BTN_SECONDARY_BG,
                hover_color=ACCENT_BLUE,
                text_color=BTN_SECONDARY_TEXT,
                border_width=1,
                border_color=BORDER_COLOR,
                command=lambda bp=b: self._restore_backup(bp),
            ).pack(side="right", padx=6, pady=4)

    def _restore_backup(self, backup_file: Path):
        try:
            shutil.copy2(backup_file, DEFAULT_GITCONFIG)
            self._reload_gitconfig_view()
            self.on_notify("Restored", f"Restored {DEFAULT_GITCONFIG.name} from backup {backup_file.name}")
        except Exception as e:
            self.on_notify("Error", f"Failed to restore backup: {e}")

    def _on_startup_check_toggled(self):
        self.manager.settings.check_updates_on_startup = bool(self.startup_check_switch.get())
        self.manager.save_settings()

    def _install_detected_update(self):
        if hasattr(self, "_cached_update_info") and self._cached_update_info and self.on_open_update:
            self.on_open_update(self._cached_update_info)
        else:
            self._check_for_updates_action()

    def _check_for_updates_action(self):
        def task():
            return self.manager.update_service.check_for_updates()

        def on_done(info: Optional[UpdateInfo]):
            if info is None:
                self.on_notify("Update Check", "Could not reach GitHub Releases (check internet connection).", is_error=True)
                return

            if info.is_update_available:
                self._cached_update_info = info
                self.ver_status_lbl.configure(
                    text=f"Installed: v{APP_VERSION}  ➔  New Version {info.latest_version} Available!",
                    text_color=ACCENT_GREEN,
                )
                self.install_update_btn.pack(side="left", padx=(0, 8))
                if self.on_open_update:
                    self.on_open_update(info)
            else:
                self._cached_update_info = None
                self.install_update_btn.pack_forget()
                self.ver_status_lbl.configure(
                    text=f"Installed Version: v{APP_VERSION} (Up to date ✓)",
                    text_color=TEXT_SECONDARY,
                )
                self.on_notify("Up to Date", f"You are running the latest version ({info.current_version}).")

        run_async(
            self,
            task_fn=task,
            on_success=on_done,
            loading_btn=self.check_update_btn,
            loading_text="⏳ Checking...",
            error_title="Update Check Error",
        )