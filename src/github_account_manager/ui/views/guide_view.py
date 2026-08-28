"""Guide View explaining the zero-switching architecture in simple, beginner-friendly language."""
from typing import Callable, Optional
import customtkinter as ctk

from github_account_manager.ui.theme import (
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    ACCENT_GREEN,
    ACCENT_ORANGE,
    BG_CARD,
    BG_INSET,
    BORDER_COLOR,
    BTN_SECONDARY_BG,
    BTN_SECONDARY_HOVER,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_HEADING,
    FONT_SMALL,
    FONT_SUBHEADING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class GuideView(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_navigate: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_navigate = on_navigate

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(22, 10))

        ctk.CTkLabel(
            header,
            text="📖 Simple Guide & Quickstart",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Learn how to use multiple GitHub accounts smoothly without ever switching manually.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(3, 0))

        # Main scrollable container
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=25, pady=(10, 20))

        # --- Section 1: How It Works in 1 Minute ---
        hero_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        hero_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            hero_card,
            text="💡 The Main Idea: Work in Separate Folders",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=18, pady=(16, 6))

        concept_text = (
            "Instead of switching accounts back and forth every time you open a project, you simply separate your projects by folder:\n\n"
            "• Put your personal projects in your Personal folder (e.g. ~/Projects/Personal)\n"
            "• Put your work projects in your Work folder (e.g. ~/Projects/Work)\n\n"
            "Git will automatically detect which folder you are in. When you make a commit or push, Git uses the correct name, email, and SSH key automatically. You never have to switch accounts by hand again!"
        )
        ctk.CTkLabel(
            hero_card,
            text=concept_text,
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            justify="left",
            wraplength=760,
        ).pack(anchor="w", padx=18, pady=(0, 16))

        # --- Section 2: Why This App Helps ---
        compare_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        compare_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            compare_card,
            text="❓ Common Problems & How This App Fixes Them",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=18, pady=(16, 8))

        grid_box = ctk.CTkFrame(compare_card, fg_color="transparent")
        grid_box.pack(fill="x", padx=18, pady=(0, 16))
        grid_box.grid_columnconfigure(0, weight=1)
        grid_box.grid_columnconfigure(1, weight=1)

        # Without app
        bad_box = ctk.CTkFrame(grid_box, fg_color=BG_INSET, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        bad_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=4)
        ctk.CTkLabel(bad_box, text="❌ Without This App:", font=FONT_BODY_BOLD, text_color=ACCENT_ORANGE).pack(anchor="w", padx=14, pady=(12, 6))
        bad_points = (
            "• Personal email accidentally shows up on work commits.\n"
            "• VS Code, Rider, or Visual Studio tries to use the wrong GitHub login.\n"
            "• You have to type 'git config user.email' for every new project.\n"
            "• Office or hotel Wi-Fi blocks SSH on port 22.\n"
            "• 'Permission Denied (publickey)' errors when pushing code."
        )
        ctk.CTkLabel(bad_box, text=bad_points, font=FONT_SMALL, text_color=TEXT_SECONDARY, justify="left").pack(anchor="w", padx=14, pady=(0, 12))

        # With app
        good_box = ctk.CTkFrame(grid_box, fg_color=BG_INSET, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        good_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=4)
        ctk.CTkLabel(good_box, text="✅ With This App:", font=FONT_BODY_BOLD, text_color=ACCENT_GREEN).pack(anchor="w", padx=14, pady=(12, 6))
        good_points = (
            "• 100% Automatic: Work in Personal folder -> Commits as Personal.\n"
            "• Work in Work folder -> Commits as Work.\n"
            "• 1-Click to stop code editors from interfering with your Git identity.\n"
            "• SSH works reliably anywhere (includes port 443 fallback).\n"
            "• Zero account switching, zero prompts, zero confusion."
        )
        ctk.CTkLabel(good_box, text=good_points, font=FONT_SMALL, text_color=TEXT_SECONDARY, justify="left").pack(anchor="w", padx=14, pady=(0, 12))

        # --- Section 3: Easy 5-Step Setup ---
        steps_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        steps_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            steps_card,
            text="🚀 Easy 5-Step Setup",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=18, pady=(16, 10))

        steps = [
            (
                "Step 1: 👤 Add Your Accounts",
                "Create your profiles (for example: 'Personal' and 'Work'). Enter your name and commit email for each account.",
                "accounts",
                "👉 Go to Accounts",
            ),
            (
                "Step 2: 🔑 Create & Link SSH Keys",
                "Generate a key for each profile. Click 'Copy Key', open github.com/settings/keys in your browser, and paste the key. Then click 'Test Connection' to confirm it works.",
                "ssh",
                "👉 Go to SSH Keys",
            ),
            (
                "Step 3: 📁 Choose Your Folders",
                "Pick the main folders on your computer for each account:\n• Example: ~/Projects/Personal -> Personal Profile\n• Example: ~/Projects/Work -> Work Profile",
                "folders",
                "👉 Go to Folders",
            ),
            (
                "Step 4: 🧩 Connect External Apps & IDEs",
                "Code editors (like VS Code, Rider, Visual Studio, and Cursor) sometimes try to use their own global login.\n• Click 'Apply Isolation' to stop editors from overriding your folder accounts.\n• Click 'Convert All Repos to SSH' so your projects use clean SSH keys.",
                "apps",
                "👉 Go to Apps",
            ),
            (
                "Step 5: 🔍 Double-Check with Inspector",
                "Pick any folder to verify that Git will use the exact name, email, and SSH key you expect.",
                "inspector",
                "👉 Go to Inspector",
            ),
        ]

        for title, desc, target_tab, btn_text in steps:
            step_box = ctk.CTkFrame(steps_card, fg_color=BG_INSET, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
            step_box.pack(fill="x", padx=18, pady=(0, 10))

            top_row = ctk.CTkFrame(step_box, fg_color="transparent")
            top_row.pack(fill="x", padx=14, pady=(10, 4))

            ctk.CTkLabel(top_row, text=title, font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(side="left")

            if self.on_navigate:
                nav_btn = ctk.CTkButton(
                    top_row,
                    text=btn_text,
                    font=FONT_SMALL,
                    height=28,
                    width=140,
                    fg_color=BTN_SECONDARY_BG,
                    hover_color=BTN_SECONDARY_HOVER,
                    text_color=ACCENT_BLUE,
                    border_width=1,
                    border_color=BORDER_COLOR,
                    command=lambda t=target_tab: self.on_navigate(t),
                )
                nav_btn.pack(side="right")

            ctk.CTkLabel(
                step_box,
                text=desc,
                font=FONT_SMALL,
                text_color=TEXT_SECONDARY,
                justify="left",
                wraplength=730,
            ).pack(anchor="w", padx=14, pady=(0, 10))

        # --- Section 4: Daily Use ---
        daily_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        daily_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            daily_card,
            text="⚡ How You Work Every Day",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=18, pady=(16, 6))

        daily_desc = (
            "Once setup is finished, you don't need to open this app every day:\n\n"
            "1. Put personal projects in your Personal folder.\n"
            "2. Put work projects in your Work folder.\n"
            "3. Commit and push normally in terminal, VS Code, Rider, or any tool:\n"
            "   git add .\n"
            "   git commit -m \"My changes\"\n"
            "   git push\n\n"
            "Git will automatically use the right email and SSH key every single time!"
        )
        ctk.CTkLabel(
            daily_card,
            text=daily_desc,
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            justify="left",
            wraplength=760,
        ).pack(anchor="w", padx=18, pady=(0, 16))