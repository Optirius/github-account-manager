"""Status badge component with dual light/dark mode support."""
import customtkinter as ctk
from github_account_manager.ui.theme import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_ORANGE,
    ACCENT_RED,
    BORDER_COLOR,
    FONT_SMALL_BOLD,
)


class StatusBadge(ctk.CTkFrame):
    def __init__(
        self,
        master,
        text: str,
        status: str = "success",  # "success", "warning", "danger", "info"
        **kwargs,
    ):
        # Backgrounds: subtle pastel in light mode, deep background in dark mode
        color_map = {
            "success": (("#dafbe1", "#1a7f37"), ("#1a7f37", "#ffffff")),
            "warning": (("#fff8c5", "#9a6700"), ("#9a6700", "#ffffff")),
            "danger": (("#ffebe9", "#cf222e"), ("#cf222e", "#ffffff")),
            "info": (("#ddf4ff", "#0969da"), ("#0969da", "#ffffff")),
        }

        # Format: (bg_light, bg_dark), (text_light, text_dark)
        cfg = color_map.get(status, (("#eaeef2", "#30363d"), ("#24292f", "#f0f6fc")))
        bg_tuple = cfg[0]
        text_tuple = cfg[1]

        super().__init__(
            master,
            fg_color=bg_tuple,
            corner_radius=6,
            border_width=1,
            border_color=BORDER_COLOR,
            **kwargs,
        )

        self.label = ctk.CTkLabel(
            self,
            text=f" {text} ",
            font=FONT_SMALL_BOLD,
            text_color=text_tuple,
        )
        self.label.pack(padx=6, pady=2)