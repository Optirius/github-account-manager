"""Folder mappings view with complete dual light/dark mode support."""
from typing import Callable, Optional
import customtkinter as ctk

from github_account_manager.models import FolderMapping
from github_account_manager.services.manager import AccountManager
from github_account_manager.ui.async_runner import run_async
from github_account_manager.ui.components.dialogs import AddFolderMappingDialog
from github_account_manager.ui.components.folder_row import FolderRow
from github_account_manager.ui.components.info_banner import InfoBanner
from github_account_manager.ui.theme import (
    ACCENT_GREEN,
    ACCENT_GREEN_HOVER,
    BORDER_COLOR,
    BTN_SECONDARY_BG,
    BTN_SECONDARY_HOVER,
    BTN_SECONDARY_TEXT,
    FONT_BODY,
    FONT_HEADING,
    FONT_SUBHEADING,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class FoldersView(ctk.CTkFrame):
    def __init__(
        self,
        master,
        manager: AccountManager,
        on_inspect: Callable[[str], None],
        on_notify: Callable[[str, str], None],
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.manager = manager
        self.on_inspect = on_inspect
        self.on_notify = on_notify

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(22, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Directory & Folder Mappings",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Repositories inside mapped folders automatically use their assigned account profile.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(3, 0))

        # Actions on right
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        self.sync_btn = ctk.CTkButton(
            btn_box,
            text="🔄 Sync Git Now",
            width=125,
            height=36,
            font=FONT_BODY,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self._handle_sync,
        )
        self.sync_btn.pack(side="left", padx=(0, 8))

        add_btn = ctk.CTkButton(
            btn_box,
            text="+ Map Directory",
            width=135,
            height=36,
            font=FONT_BODY,
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=self._open_add_dialog,
        )
        add_btn.pack(side="left")

        # Scrollable Mappings Container
        self.rows_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.rows_scroll.pack(fill="both", expand=True, padx=25, pady=(10, 20))

        self.refresh()

    def refresh(self):
        for widget in self.rows_scroll.winfo_children():
            widget.destroy()

        # Contextual explanation banner
        InfoBanner(
            self.rows_scroll,
            title="How Directory Mappings Work",
            what_it_does="Binds entire workspace directories (e.g. D:/Personal or D:/Professional) to a specific GitHub profile.",
            why_needed="You never have to run 'git config user.email' manually again—Git automatically routes all repositories inside the folder to the correct profile.",
            how_it_works="Injects conditional '[includeIf \"gitdir/i:...\"]' blocks into ~/.gitconfig so Git natively activates the right identity on the fly.",
            icon="📁",
        ).pack(fill="x", pady=(0, 15))

        mappings = self.manager.settings.folder_mappings
        accounts = {a.id: a for a in self.manager.settings.accounts}

        if not mappings:
            empty_box = ctk.CTkFrame(self.rows_scroll, fg_color="transparent")
            empty_box.pack(fill="both", expand=True, pady=60)
            ctk.CTkLabel(
                empty_box,
                text="No directory mappings configured.",
                font=FONT_SUBHEADING,
                text_color=TEXT_MUTED,
            ).pack()
            ctk.CTkLabel(
                empty_box,
                text="Click '+ Map Directory' to link folders like D:/Personal to an account.",
                font=FONT_BODY,
                text_color=TEXT_MUTED,
            ).pack(pady=(4, 0))
            return

        for mapping in mappings:
            acc = accounts.get(mapping.account_id)
            row = FolderRow(
                self.rows_scroll,
                mapping=mapping,
                account=acc,
                on_inspect=self.on_inspect,
                on_delete=self._handle_delete,
            )
            row.pack(fill="x", pady=5)

    def _open_add_dialog(self):
        if not self.manager.settings.accounts:
            self.on_notify("Notice", "Please create at least one Account Profile first.")
            return

        def handle_add(path: str, account_id: str):
            self.manager.add_folder_mapping(path, account_id)
            self.on_notify("Mapping Added", f"Mapped '{path}' to selected account.")
            self.refresh()

        AddFolderMappingDialog(
            self.winfo_toplevel(),
            accounts=self.manager.settings.accounts,
            on_add=handle_add,
        )

    def _handle_delete(self, mapping: FolderMapping):
        self.manager.remove_folder_mapping(mapping.id)
        self.on_notify("Mapping Removed", f"Removed mapping for {mapping.folder_path}")
        self.refresh()

    def _handle_sync(self):
        def task():
            self.manager.sync_git()

        def on_done(_):
            self.on_notify("Git Synchronized", "Updated ~/.gitconfig & ~/.ssh/config with current directory rules.")

        run_async(
            self,
            task_fn=task,
            on_success=on_done,
            loading_btn=self.sync_btn,
            loading_text="⏳ Syncing...",
            error_title="Git Sync Error",
        )