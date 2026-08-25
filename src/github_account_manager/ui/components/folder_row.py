"""Folder row widget with proper light and dark mode colors and readable typography."""
import os
from typing import Callable, Optional
import customtkinter as ctk

from github_account_manager.models import Account, FolderMapping
from github_account_manager.ui.theme import (
    ACCENT_RED,
    BG_CARD,
    BORDER_COLOR,
    BTN_SECONDARY_BG,
    BTN_SECONDARY_HOVER,
    BTN_SECONDARY_TEXT,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class FolderRow(ctk.CTkFrame):
    def __init__(
        self,
        master,
        mapping: FolderMapping,
        account: Optional[Account],
        on_inspect: Callable[[str], None],
        on_delete: Callable[[FolderMapping], None],
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            **kwargs,
        )
        self.mapping = mapping
        self.account = account
        self.on_inspect = on_inspect
        self.on_delete = on_delete

        self._build_ui()

    def _build_ui(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=14)

        # Folder Icon + Path
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        path_label = ctk.CTkLabel(
            left,
            text=f"📁  {self.mapping.normalized_path}",
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
        )
        path_label.pack(anchor="w")

        # Account details underneath
        if self.account:
            acc_desc = f"Mapped to: {self.account.name} ({self.account.email})"
            acc_lbl = ctk.CTkLabel(
                left,
                text=acc_desc,
                font=FONT_BODY,
                text_color=TEXT_SECONDARY,
            )
            acc_lbl.pack(anchor="w", pady=(3, 0))
        else:
            acc_lbl = ctk.CTkLabel(
                left,
                text="⚠️ Account removed or missing",
                font=FONT_BODY,
                text_color=ACCENT_RED,
            )
            acc_lbl.pack(anchor="w", pady=(3, 0))

        # Right Action Buttons
        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="right")

        # Inspect button
        inspect_btn = ctk.CTkButton(
            actions,
            text="🔍 Inspect",
            width=90,
            height=32,
            font=FONT_SMALL,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=lambda: self.on_inspect(self.mapping.folder_path),
        )
        inspect_btn.pack(side="left", padx=5)

        # Open in Explorer button
        open_btn = ctk.CTkButton(
            actions,
            text="📂 Open",
            width=80,
            height=32,
            font=FONT_SMALL,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self._open_in_explorer,
        )
        open_btn.pack(side="left", padx=5)

        # Delete button
        del_btn = ctk.CTkButton(
            actions,
            text="🗑️",
            width=36,
            height=32,
            fg_color=BTN_SECONDARY_BG,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=BTN_SECONDARY_TEXT,
            hover_color=ACCENT_RED,
            command=lambda: self.on_delete(self.mapping),
        )
        del_btn.pack(side="left", padx=(5, 0))

    def _open_in_explorer(self):
        try:
            os.startfile(self.mapping.folder_path)
        except Exception:
            pass