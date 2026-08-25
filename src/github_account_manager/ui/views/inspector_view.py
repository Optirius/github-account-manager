"""Inspector view for live inspection and diagnostic testing of directory git configurations."""
from pathlib import Path
import threading
import tkinter.filedialog as fd
from typing import Callable, Optional
import customtkinter as ctk

from github_account_manager.services.manager import AccountManager
from github_account_manager.ui.async_runner import run_async
from github_account_manager.ui.components.dialogs import (
    ResultModalDialog,
    SSHTestGuideDialog,
)
from github_account_manager.ui.components.info_banner import InfoBanner
from github_account_manager.ui.components.status_badge import StatusBadge
from github_account_manager.ui.theme import (
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    ACCENT_GREEN,
    BG_CARD,
    BG_INSET,
    BORDER_COLOR,
    BTN_SECONDARY_BG,
    BTN_SECONDARY_HOVER,
    BTN_SECONDARY_TEXT,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_HEADING,
    FONT_MONO,
    FONT_MONO_SMALL,
    FONT_SMALL,
    FONT_SUBHEADING,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class InspectorView(ctk.CTkFrame):
    def __init__(self, master, manager: AccountManager, on_notify: Callable[[str, str], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.manager = manager
        self.on_notify = on_notify

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(22, 10))

        ctk.CTkLabel(
            header,
            text="Git & Directory Inspector",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Test any directory to verify which Git account and SSH key will be used in practice.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(3, 0))

        # Main content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=(10, 20))

        # Contextual explanation banner
        InfoBanner(
            content,
            title="How the Directory Inspector Works",
            what_it_does="Inspects any folder or repository to simulate and display the exact Git username, email, and SSH command Git will resolve.",
            why_needed="Allows you to verify with 100% certainty that your folder rules and SSH keys are active before making commits or pushes.",
            how_it_works="Executes non-destructive Git configuration queries and verifies live SSH handshake against GitHub.",
            icon="🔍",
        ).pack(fill="x", pady=(0, 15))

        # Folder selection card
        picker_card = ctk.CTkFrame(content, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        picker_card.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(picker_card, text="Select Folder / Repository to Inspect:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(14, 6))

        row = ctk.CTkFrame(picker_card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 14))

        self.path_entry = ctk.CTkEntry(row, placeholder_text="e.g. D:/Personal/Projects/my-project", height=36, font=FONT_BODY)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        if self.manager.settings.folder_mappings:
            self.path_entry.insert(0, self.manager.settings.folder_mappings[0].folder_path)

        browse_btn = ctk.CTkButton(
            row,
            text="Browse...",
            width=90,
            height=36,
            font=FONT_SMALL,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self._browse_folder,
        )
        browse_btn.pack(side="left", padx=(0, 8))

        self.inspect_btn = ctk.CTkButton(
            row,
            text="🔍 Inspect Now",
            width=130,
            height=36,
            font=FONT_BODY_BOLD,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            text_color="#ffffff",
            command=self.run_inspection,
        )
        self.inspect_btn.pack(side="left")

        # Results Card
        self.result_card = ctk.CTkFrame(content, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        self.result_card.pack(fill="both", expand=True)

        self.res_scroll = ctk.CTkScrollableFrame(self.result_card, fg_color="transparent")
        self.res_scroll.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            self.res_scroll,
            text="Enter a directory path above and click 'Inspect Now' to view its active Git identity.",
            font=FONT_BODY,
            text_color=TEXT_MUTED,
        ).pack(pady=40)

    def _browse_folder(self):
        chosen = fd.askdirectory(title="Select Directory to Inspect")
        if chosen:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, chosen)
            self.run_inspection()

    def inspect_path(self, path_str: str):
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, path_str)
        self.run_inspection()

    def run_inspection(self):
        target = self.path_entry.get().strip()
        if not target:
            return

        def task():
            info = self.manager.git_service.inspect_directory(target)
            matched_account = self.manager.get_account_for_folder(target)
            return info, matched_account

        def on_done(result):
            info, matched_account = result
            for w in self.res_scroll.winfo_children():
                w.destroy()

            # Header of result
            res_header = ctk.CTkFrame(self.res_scroll, fg_color="transparent")
            res_header.pack(fill="x", pady=(0, 10))

            ctk.CTkLabel(
                res_header,
                text=f"Inspection Results for: {target}",
                font=FONT_SUBHEADING,
                text_color=TEXT_PRIMARY,
            ).pack(side="left")

            if info.get("is_git_repo"):
                StatusBadge(res_header, "Git Repository", "info").pack(side="right")
            elif info.get("exists"):
                StatusBadge(res_header, "Standard Directory", "warning").pack(side="right")
            else:
                StatusBadge(res_header, "Directory Not Found", "danger").pack(side="right")

            # Matched App Account
            acc_box = ctk.CTkFrame(self.res_scroll, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
            acc_box.pack(fill="x", pady=8)

            if matched_account:
                ctk.CTkLabel(
                    acc_box,
                    text=f"✓ Mapped Profile: {matched_account.name}",
                    font=FONT_BODY_BOLD,
                    text_color=ACCENT_GREEN,
                ).pack(anchor="w", padx=14, pady=(10, 2))
                ctk.CTkLabel(
                    acc_box,
                    text=f"Config file: ~/.gitconfig-{matched_account.slug}",
                    font=FONT_MONO_SMALL,
                    text_color=TEXT_SECONDARY,
                ).pack(anchor="w", padx=14, pady=(0, 10))
            else:
                ctk.CTkLabel(
                    acc_box,
                    text="ℹ️ No direct folder mapping found (Global default Git config applies)",
                    font=FONT_BODY,
                    text_color=TEXT_SECONDARY,
                ).pack(anchor="w", padx=14, pady=10)

            # Table of resolved values
            table = ctk.CTkFrame(self.res_scroll, fg_color="transparent")
            table.pack(fill="x", pady=8)

            def add_row(label: str, val: str, is_mono: bool = False):
                r = ctk.CTkFrame(table, fg_color="transparent")
                r.pack(fill="x", pady=4)
                ctk.CTkLabel(r, text=label, width=180, font=FONT_BODY_BOLD, text_color=TEXT_SECONDARY, anchor="w").pack(side="left")
                font_to_use = FONT_MONO if is_mono else FONT_BODY
                display_val = val or "(empty / not configured)"
                color = TEXT_PRIMARY if val else TEXT_MUTED
                ctk.CTkLabel(r, text=display_val, font=font_to_use, text_color=color, anchor="w").pack(side="left", fill="x", expand=True)

            add_row("Resolved user.name:", info.get("user_name", ""))
            add_row("Resolved user.email:", info.get("user_email", ""))
            add_row("Resolved core.sshCommand:", info.get("ssh_command", ""), is_mono=True)

            # Test SSH button
            if matched_account and matched_account.ssh_key_path:
                btn_box = ctk.CTkFrame(self.res_scroll, fg_color="transparent")
                btn_box.pack(fill="x", pady=15)

                test_btn = ctk.CTkButton(
                    btn_box,
                    text=f"⚡ Test SSH Connection using {matched_account.name} Key",
                    fg_color=ACCENT_BLUE,
                    hover_color=ACCENT_BLUE_HOVER,
                    text_color="#ffffff",
                    height=36,
                    font=FONT_BODY_BOLD,
                )
                test_btn.configure(command=lambda a=matched_account, b=test_btn: self._test_account_ssh(a, b))
                test_btn.pack(anchor="w")

        run_async(
            self,
            task_fn=task,
            on_success=on_done,
            loading_btn=self.inspect_btn,
            loading_text="⏳ Inspecting...",
            error_title="Inspection Error",
        )

    def _test_account_ssh(self, account, btn: Optional[ctk.CTkButton] = None):
        pub_content = self.manager.ssh_service.read_public_key(account.ssh_key_path) or ""
        self.on_notify("Testing SSH", f"Connecting to GitHub using '{account.name}' key...")

        def task():
            return self.manager.test_ssh_for_account(account.id)

        def on_done(result):
            success, output, user = result
            SSHTestGuideDialog(
                self.winfo_toplevel(),
                key_name=account.name,
                public_key_content=pub_content,
                is_connected=success,
                output=output,
                username=user,
            )

        run_async(
            self,
            task_fn=task,
            on_success=on_done,
            loading_btn=btn,
            loading_text="⏳ Testing...",
            error_title="SSH Test Error",
        )