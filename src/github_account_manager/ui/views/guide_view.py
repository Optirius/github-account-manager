"""Guide View explaining the zero-switching architecture and step-by-step app setup."""
from typing import Callable, Optional
import customtkinter as ctk

from github_account_manager.ui.theme import (
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    ACCENT_GREEN,
    ACCENT_GREEN_HOVER,
    ACCENT_ORANGE,
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
            text="User Guide & Zero-Switching Architecture",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Understand how automatic Git account routing works and how to set it up step-by-step.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(3, 0))

        # Main scrollable container
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=25, pady=(10, 20))

        # --- Section 1: The Core Concept: Zero-Switching ---
        hero_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        hero_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            hero_card,
            text="🌟 The Core Concept: Never Switch Accounts Manually Again",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=18, pady=(16, 6))

        concept_p1 = (
            "Most developers struggle with multi-account setups because they try to switch accounts manually, "
            "re-configure Git per repository, or use confusing SSH host alias tricks in clone URLs.\n\n"
            "This application uses a Zero-Switching Architecture powered by Git's native conditional routing: "
            "You assign root workspace directories (e.g. D:/Personal and D:/Professional) to account profiles once. "
            "From then on, Git automatically detects which folder you are working in and applies the correct commit author, "
            "email, and SSH key on the fly."
        )
        ctk.CTkLabel(
            hero_card,
            text=concept_p1,
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            justify="left",
            wraplength=760,
        ).pack(anchor="w", padx=18, pady=(0, 16))

        # --- Section 2: Why You Need This App ---
        compare_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        compare_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            compare_card,
            text="🤔 Do You Need This Application?",
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
        ctk.CTkLabel(bad_box, text="❌ Without This App (The Pain):", font=FONT_BODY_BOLD, text_color=ACCENT_ORANGE).pack(anchor="w", padx=14, pady=(12, 6))
        bad_points = (
            "• Personal emails leak into workplace repositories.\n"
            "• VS Code uses your work login and denies access to personal repos.\n"
            "• You have to run 'git config user.email' for every new project.\n"
            "• SSH authentication fails on port 22 due to firewalls or ISP blocks.\n"
            "• Confusing URL rewrites like 'git@github-personal:...'"
        )
        ctk.CTkLabel(bad_box, text=bad_points, font=FONT_SMALL, text_color=TEXT_SECONDARY, justify="left").pack(anchor="w", padx=14, pady=(0, 12))

        # With app
        good_box = ctk.CTkFrame(grid_box, fg_color=BG_INSET, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        good_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=4)
        ctk.CTkLabel(good_box, text="✅ With This App (Zero Friction):", font=FONT_BODY_BOLD, text_color=ACCENT_GREEN).pack(anchor="w", padx=14, pady=(12, 6))
        good_points = (
            "• 100% automated: Work in D:/Personal -> commits as Personal.\n"
            "• Work in D:/Professional -> commits as Professional.\n"
            "• 1-Click IDE isolation prevents VS Code from overriding folders.\n"
            "• Standard 'git@github.com:...' remotes with port 443 reliability.\n"
            "• Zero account switching, zero prompts, zero credential confusion."
        )
        ctk.CTkLabel(good_box, text=good_points, font=FONT_SMALL, text_color=TEXT_SECONDARY, justify="left").pack(anchor="w", padx=14, pady=(0, 12))

        # --- Section 3: 5-Step Setup Walkthrough ---
        steps_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        steps_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            steps_card,
            text="🚀 5-Step Setup Guide (Page by Page)",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=18, pady=(16, 10))

        steps = [
            (
                "Step 1: 👤 Accounts & Profiles",
                "Define your identity profiles (e.g. 'Personal' and 'Professional'). "
                "Set your exact Git Author Name (e.g. Tahmid Hossain) and Git Commit Email for each profile.",
                "accounts",
                "👉 Open Accounts Tab",
            ),
            (
                "Step 2: 🔑 SSH Key Management",
                "Create high-security ED25519 SSH keys for your profiles. Click '📋 Copy Key' and add it to your GitHub account (Settings > SSH and GPG keys). "
                "Use '⚡ Test Connection' to verify live authentication.",
                "ssh",
                "👉 Open SSH Keys Tab",
            ),
            (
                "Step 3: 📁 Directory Mappings",
                "Map your workspace root directories (e.g. D:/Personal and D:/Professional) to their corresponding profile. "
                "Git automatically injects conditional includes so all repositories inside inherit the profile.",
                "folders",
                "👉 Open Folders Tab",
            ),
            (
                "Step 4: 🧩 External Apps & IDE Isolation",
                "External code editors (VS Code, Cursor) often inject their logged-in account and Windows Credential Manager caches global HTTPS tokens.\n"
                "• Click '⚡ Apply Isolation to All IDEs' to stop editors from hijacking Git.\n"
                "• Click '🚀 Convert All HTTPS Repos to SSH' to route repositories through clean SSH.",
                "apps",
                "👉 Open Apps Tab",
            ),
            (
                "Step 5: 🔍 Git & Directory Inspector",
                "Browse or paste any folder path to verify what Git author identity and SSH key Git will use in real time.",
                "inspector",
                "👉 Open Inspector Tab",
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
                    width=150,
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

        # --- Section 4: Daily Workflow ---
        daily_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        daily_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            daily_card,
            text="⚡ Daily Workflow: How You Work Going Forward",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=18, pady=(16, 6))

        daily_desc = (
            "Once setup is complete, you do NOT need to open this app every day.\n\n"
            "1. When working on personal projects, clone or place them in your Personal directory (e.g. D:/Personal/Projects/my-app).\n"
            "2. When working on company or client projects, clone or place them in your Work directory (e.g. D:/Professional/Projects/work-app).\n"
            "3. Use Git normally via terminal, VS Code, Cursor, or any GUI: 'git commit -m \"feat: new feature\"' & 'git push'.\n\n"
            "Git natively commits with the right email and authenticates with the right SSH key without a single click or prompt!"
        )
        ctk.CTkLabel(
            daily_card,
            text=daily_desc,
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            justify="left",
            wraplength=760,
        ).pack(anchor="w", padx=18, pady=(0, 16))