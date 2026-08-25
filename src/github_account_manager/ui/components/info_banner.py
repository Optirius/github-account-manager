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
        self._desc_labels: List[ctk.CTkLabel] = []

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

        # Body Frame containing structured grid explanation
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid_columnconfigure(0, weight=0, minsize=145)
        self.body.grid_columnconfigure(1, weight=1)

        items = [
            ("🎯 What it does:", what_it_does),
            ("💡 Why it's needed:", why_needed),
        ]
        if how_it_works:
            items.append(("⚙️ How it works:", how_it_works))

        for row_idx, (lbl_text, desc_text) in enumerate(items):
            # Left title label (Top-Left aligned)
            k_lbl = ctk.CTkLabel(
                self.body,
                text=lbl_text,
                font=FONT_SMALL_BOLD,
                text_color=TEXT_PRIMARY,
                anchor="nw",
                justify="left",
            )
            k_lbl.grid(row=row_idx, column=0, sticky="nw", padx=(0, 10), pady=3)

            # Right description label (Top-Left aligned, responsive wrapping)
            v_lbl = ctk.CTkLabel(
                self.body,
                text=desc_text,
                font=FONT_SMALL,
                text_color=TEXT_SECONDARY,
                anchor="nw",
                justify="left",
                wraplength=580,
            )
            v_lbl.grid(row=row_idx, column=1, sticky="new", pady=3)
            self._desc_labels.append(v_lbl)

        self.body.bind("<Configure>", self._on_body_resize)

        if not collapsed:
            self.body.pack(fill="x", padx=14, pady=(0, 12))

    def _on_body_resize(self, event):
        wrap_w = max(200, event.width - 165)
        for lbl in self._desc_labels:
            try:
                lbl.configure(wraplength=wrap_w)
            except Exception:
                pass

    def _toggle(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.body.pack_forget()
            self.toggle_btn.configure(text="▼ Learn More")
        else:
            self.body.pack(fill="x", padx=14, pady=(0, 12))
            self.toggle_btn.configure(text="▲ Hide Info")