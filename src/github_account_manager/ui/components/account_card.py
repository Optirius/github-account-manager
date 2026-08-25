"""Account card widget with complete light and dark theme support."""
from typing import Callable, Optional
import customtkinter as ctk

from github_account_manager.models import Account
from github_account_manager.ui.components.status_badge import StatusBadge
from github_account_manager.ui.theme import (
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    ACCENT_GREEN,
    ACCENT_GREEN_HOVER,
    ACCENT_RED,
    ACCENT_RED_HOVER,
    BG_CARD,
    BG_INSET,
    BORDER_COLOR,
    BTN_SECONDARY_BG,
    BTN_SECONDARY_HOVER,
    BTN_SECONDARY_TEXT,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_MONO_SMALL,
    FONT_SMALL,
    FONT_SUBHEADING,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class AccountCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        account: Account,
        on_edit: Callable[[Account], None],
        on_delete: Callable[[Account], None],
        on_test_ssh: Callable[[Account], None],
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=BORDER_COLOR,
            **kwargs,
        )
        self.account = account
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_test_ssh = on_test_ssh

        self._build_ui()

    def _build_ui(self):
        # Header Row: Name & Status Badges
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 6))

        title_lbl = ctk.CTkLabel(
            header,
            text=f"👤  {self.account.name}",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        )
        title_lbl.pack(side="left")

        # Badges on right
        badge_box = ctk.CTkFrame(header, fg_color="transparent")
        badge_box.pack(side="right")

        if self.account.ssh_key_path:
            StatusBadge(badge_box, "SSH Linked", "info").pack(side="left", padx=4)
        else:
            StatusBadge(badge_box, "No SSH Key", "danger").pack(side="left", padx=4)

        # Body: Info Details
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=6)

        left_col = ctk.CTkFrame(body, fg_color="transparent")
        left_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            left_col,
            text=f"Git Author:  {self.account.git_name} <{self.account.email}>",
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=1)

        handle_text = f"GitHub Handle: @{self.account.username}" if self.account.username else "GitHub Handle: (not linked)"
        ctk.CTkLabel(
            left_col,
            text=handle_text,
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=1)

        key_name = self.account.ssh_key_path or "None"
        ctk.CTkLabel(
            left_col,
            text=f"SSH Key: {key_name}",
            font=FONT_MONO_SMALL,
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=3)

        # Separator line
        sep = ctk.CTkFrame(self, height=1, fg_color=BORDER_COLOR)
        sep.pack(fill="x", padx=18, pady=10)

        # Action Buttons Row
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(0, 16))

        # Test SSH button
        test_ssh_btn = ctk.CTkButton(
            actions,
            text="⚡ Test SSH",
            width=105,
            height=32,
            font=FONT_SMALL,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=lambda: self.on_test_ssh(self.account),
        )
        test_ssh_btn.pack(side="left", padx=(0, 8))

        # Right side actions: Edit & Delete
        del_btn = ctk.CTkButton(
            actions,
            text="🗑️",
            width=36,
            height=32,
            font=FONT_BODY,
            fg_color=BTN_SECONDARY_BG,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=BTN_SECONDARY_TEXT,
            hover_color=ACCENT_RED,
            command=lambda: self.on_delete(self.account),
        )
        del_btn.pack(side="right")

        edit_btn = ctk.CTkButton(
            actions,
            text="✏️ Edit",
            width=75,
            height=32,
            font=FONT_SMALL,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=lambda: self.on_edit(self.account),
        )
        edit_btn.pack(side="right", padx=(0, 8))