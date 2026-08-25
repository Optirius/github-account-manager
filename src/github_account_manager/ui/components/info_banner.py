"""Reusable Contextual Info Banner component explaining What it is, Why it's needed, and How it works."""
from typing import List, Optional, Tuple
import customtkinter as ctk

from github_account_manager.ui.theme import (
    ACCENT_BLUE,
    BG_INSET,
    BORDER_COLOR,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class InfoBanner(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str,
        what_it_does: str,
        why_needed: str,
        how_it_works: Optional[str] = None,
        icon: str = "💡",
        collapsed: bool = False,
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=BG_INSET,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            **kwargs,
        )
        self.collapsed = collapsed

        # Header Frame (Clickable for toggle)
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=14, pady=10)

        left_box = ctk.CTkFrame(self.header, fg_color="transparent")
        left_box.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            left_box,
            text=f"{icon}  {title}",
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        # Toggle indicator button
        self.toggle_btn = ctk.CTkButton(
            self.header,
            text="▲ Hide Info" if not collapsed else "▼ Learn More",
            font=FONT_SMALL,
            width=90,
            height=24,
            fg_color="transparent",
            text_color=ACCENT_BLUE,
            hover=False,
            command=self._toggle,
        )
        self.toggle_btn.pack(side="right")

        # Body Frame containing structured explanation
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        if not collapsed:
            self.body.pack(fill="x", padx=14, pady=(0, 12))

        # 1. What it does
        self._add_item("🎯 What it does:", what_it_does)

        # 2. Why it's needed
        self._add_item("💡 Why it's needed:", why_needed)

        # 3. How it works
        if how_it_works:
            self._add_item("⚙️ How it works:", how_it_works)

    def _add_item(self, label: str, text: str):
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=2)

        ctk.CTkLabel(
            row,
            text=label,
            font=FONT_SMALL_BOLD,
            text_color=TEXT_PRIMARY,
            width=130,
            anchor="nw",
        ).pack(side="left", anchor="n")

        ctk.CTkLabel(
            row,
            text=text,
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
            justify="left",
            wraplength=700,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

    def _toggle(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.body.pack_forget()
            self.toggle_btn.configure(text="▼ Learn More")
        else:
            self.body.pack(fill="x", padx=14, pady=(0, 12))
            self.toggle_btn.configure(text="▲ Hide Info")