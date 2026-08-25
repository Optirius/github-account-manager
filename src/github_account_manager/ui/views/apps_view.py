"""View for managing external IDEs (VS Code), Windows Credential Manager, and repo remotes."""
from pathlib import Path
import threading
from typing import Callable, Optional
import customtkinter as ctk

from github_account_manager.services.manager import AccountManager
from github_account_manager.ui.components.dialogs import ConfirmDeleteDialog
from github_account_manager.ui.components.status_badge import StatusBadge
from github_account_manager.ui.theme import (
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    ACCENT_GREEN,
    ACCENT_GREEN_HOVER,
    ACCENT_ORANGE,
    ACCENT_RED,
    ACCENT_RED_HOVER,
    BG_APP,
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
    FONT_SMALL_BOLD,
    FONT_SUBHEADING,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class AppsView(ctk.CTkFrame):
    def __init__(self, master, manager: AccountManager, on_notify: Callable[[str, str], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.manager = manager
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
            text="External Apps & Git Credential Manager",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Enforce folder-specific accounts in VS Code, IDEs, and Git Credential Manager.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(3, 0))

        refresh_btn = ctk.CTkButton(
            header,
            text="🔄 Refresh All",
            width=110,
            height=36,
            font=FONT_BODY,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self.refresh,
        )
        refresh_btn.pack(side="right")

        # Scrollable Content
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=25, pady=(10, 20))

        self.refresh()

    def refresh(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()

        self._render_vscode_section()
        self._render_credentials_section()
        self._render_repo_converter_section()

    # --- Section 1: VS Code Isolation ---

    def _render_vscode_section(self):
        card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(0, 16))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            header,
            text="💻  Visual Studio Code - Git Account Isolation",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        vs_status = self.manager.app_service.get_vscode_status()

        if vs_status.get("is_isolated"):
            StatusBadge(header, "Folder-Aware (Isolated)", "active").pack(side="right")
        elif vs_status.get("installed"):
            StatusBadge(header, "Account Interception Active", "warning").pack(side="right")
        else:
            StatusBadge(header, "Not Detected", "neutral").pack(side="right")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(
            body,
            text="By default, VS Code's GitHub integration supplies its logged-in account to Git operations across all folders.\n"
                 "Enabling Folder Isolation forces VS Code to strictly respect your folder rules and SSH keys.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        status_box = ctk.CTkFrame(body, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
        status_box.pack(fill="x", pady=(0, 12))

        def add_status_row(label: str, active: bool):
            r = ctk.CTkFrame(status_box, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(r, text=label, font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, width=230, anchor="w").pack(side="left")
            status_text = "Disabled (Isolated ✓)" if active else "Enabled (May Override Account ⚠️)"
            color = ACCENT_GREEN if active else ACCENT_ORANGE
            ctk.CTkLabel(r, text=status_text, font=FONT_BODY, text_color=color).pack(side="left")

        add_status_row("github.gitAuthentication:", vs_status.get("git_auth_disabled", False))
        add_status_row("git.terminalAuthentication:", vs_status.get("terminal_auth_disabled", False))

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x")

        apply_btn = ctk.CTkButton(
            btn_row,
            text="⚡ Apply Folder Isolation in VS Code",
            font=FONT_BODY_BOLD,
            height=34,
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=self._apply_vscode_isolation,
        )
        apply_btn.pack(side="left", padx=(0, 8))

        restore_btn = ctk.CTkButton(
            btn_row,
            text="↩️ Restore VS Code Defaults",
            font=FONT_SMALL,
            height=34,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self._restore_vscode_defaults,
        )
        restore_btn.pack(side="left")

    def _apply_vscode_isolation(self):
        success, msg = self.manager.app_service.apply_vscode_isolation()
        if success:
            self.on_notify("VS Code Configured", msg)
            self.refresh()
        else:
            self.on_notify("Error", msg, is_error=True)

    def _restore_vscode_defaults(self):
        success, msg = self.manager.app_service.restore_vscode_defaults()
        if success:
            self.on_notify("Restored", msg)
            self.refresh()
        else:
            self.on_notify("Error", msg, is_error=True)

    # --- Section 2: Windows Git Credential Manager (GCM) ---

    def _render_credentials_section(self):
        card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(0, 16))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            header,
            text="🔐  Windows Credential Manager (Git / GitHub)",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(
            body,
            text="When using HTTPS remotes, Git Credential Manager caches one global account (e.g. git:https://github.com).\n"
                 "If a cached credential exists, it can override personal repositories and cause Permission Denied errors.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        creds = self.manager.app_service.list_windows_git_credentials()

        if not creds:
            empty_box = ctk.CTkFrame(body, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
            empty_box.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(
                empty_box,
                text="✓ No global Git credentials found in Windows Credential Manager. Clean state!",
                font=FONT_BODY,
                text_color=ACCENT_GREEN,
            ).pack(padx=14, pady=10, anchor="w")
        else:
            table_box = ctk.CTkFrame(body, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
            table_box.pack(fill="x", pady=(0, 12))

            for c in creds:
                target = c.get("Target", "")
                user = c.get("User", "(unknown)")
                display_target = target.replace("LegacyGeneric:target=", "")

                row = ctk.CTkFrame(table_box, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=6)

                info_col = ctk.CTkFrame(row, fg_color="transparent")
                info_col.pack(side="left", fill="x", expand=True)

                ctk.CTkLabel(
                    info_col,
                    text=f"🔑  {display_target}",
                    font=FONT_BODY_BOLD,
                    text_color=TEXT_PRIMARY,
                    anchor="w",
                ).pack(anchor="w")

                ctk.CTkLabel(
                    info_col,
                    text=f"Cached User: @{user} (Forces this user for HTTPS git operations)",
                    font=FONT_SMALL,
                    text_color=ACCENT_ORANGE,
                    anchor="w",
                ).pack(anchor="w")

                del_btn = ctk.CTkButton(
                    row,
                    text="🗑️ Clear Credential",
                    font=FONT_SMALL,
                    width=135,
                    height=28,
                    fg_color=BTN_SECONDARY_BG,
                    hover_color=ACCENT_RED,
                    text_color=BTN_SECONDARY_TEXT,
                    border_width=1,
                    border_color=BORDER_COLOR,
                    command=lambda t=target, u=user: self._delete_credential(t, u),
                )
                del_btn.pack(side="right")

        gcm_btn_row = ctk.CTkFrame(body, fg_color="transparent")
        gcm_btn_row.pack(fill="x")

        http_path_btn = ctk.CTkButton(
            gcm_btn_row,
            text="⚡ Enable 'credential.useHttpPath = true'",
            font=FONT_BODY,
            height=34,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            text_color="#ffffff",
            command=self._enable_http_path,
        )
        http_path_btn.pack(side="left")

    def _delete_credential(self, target: str, user: str):
        def confirm():
            success, msg = self.manager.app_service.delete_windows_credential(target)
            if success:
                self.on_notify("Credential Cleared", f"Cleared cached credential for @{user}.")
                self.refresh()
            else:
                self.on_notify("Error", msg, is_error=True)

        clean_t = target.replace("LegacyGeneric:target=", "")
        ConfirmDeleteDialog(
            self.winfo_toplevel(),
            title="Clear Windows Git Credential",
            heading=f"Clear Credential for @{user}?",
            message=f"This will remove '{clean_t}' from Windows Credential Manager.\n\n"
                    f"Git and external apps will stop automatically injecting @{user}'s credentials into HTTPS repositories.",
            on_confirm=confirm,
        )

    def _enable_http_path(self):
        success, msg = self.manager.app_service.enable_git_credential_use_http_path()
        if success:
            self.on_notify("Configured", msg)
        else:
            self.on_notify("Error", msg, is_error=True)

    # --- Section 3: Repository Remote Converter (HTTPS -> SSH) ---

    def _render_repo_converter_section(self):
        card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(0, 16))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            header,
            text="🔄  Repository Remote Protocols (HTTPS ➔ SSH Converter)",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        repos = self.manager.app_service.scan_repositories(self.manager.settings.folder_mappings)
        https_count = sum(1 for r in repos if r.get("protocol") == "HTTPS")

        if https_count > 0:
            bulk_btn = ctk.CTkButton(
                header,
                text=f"🚀 Convert All {https_count} HTTPS Repos to SSH",
                font=FONT_BODY_BOLD,
                height=32,
                fg_color=ACCENT_GREEN,
                hover_color=ACCENT_GREEN_HOVER,
                text_color="#ffffff",
                command=lambda: self._convert_all_to_ssh(repos),
            )
            bulk_btn.pack(side="right")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(
            body,
            text="SSH remotes (git@github.com:owner/repo.git) are 100% immune to VS Code credential hijacking.\n"
                 "Converting repositories from HTTPS to SSH ensures Git always authenticates with the correct account.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        if not repos:
            empty_box = ctk.CTkFrame(body, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
            empty_box.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(
                empty_box,
                text="No Git repositories found in your mapped directories.",
                font=FONT_BODY,
                text_color=TEXT_MUTED,
            ).pack(padx=14, pady=10, anchor="w")
            return

        for repo in repos:
            self._render_repo_row(body, repo)

    def _render_repo_row(self, parent, repo: dict):
        row = ctk.CTkFrame(parent, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
        row.pack(fill="x", pady=4)

        top_line = ctk.CTkFrame(row, fg_color="transparent")
        top_line.pack(fill="x", padx=12, pady=(8, 2))

        ctk.CTkLabel(
            top_line,
            text=f"📁  {repo['name']}",
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        # Find matching account name
        acc = next((a for a in self.manager.settings.accounts if a.id == repo["account_id"]), None)
        acc_label = f"Assigned: {acc.name}" if acc else "Assigned Account"

        ctk.CTkLabel(
            top_line,
            text=f"({acc_label})",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=8)

        # Protocol badge
        proto = repo.get("protocol", "Local")
        badge_variant = "active" if proto == "SSH" else ("warning" if proto == "HTTPS" else "neutral")
        badge_text = "SSH (Safe & Isolated ✓)" if proto == "SSH" else ("HTTPS (Hijack Risk ⚠️)" if proto == "HTTPS" else proto)
        StatusBadge(top_line, badge_text, badge_variant).pack(side="right")

        # Bottom details line
        bot_line = ctk.CTkFrame(row, fg_color="transparent")
        bot_line.pack(fill="x", padx=12, pady=(2, 8))

        ctk.CTkLabel(
            bot_line,
            text=repo.get("remote_url") or "(no origin remote)",
            font=FONT_MONO_SMALL,
            text_color=TEXT_SECONDARY,
        ).pack(side="left")

        if proto == "HTTPS":
            conv_btn = ctk.CTkButton(
                bot_line,
                text="⚡ Convert to SSH",
                font=FONT_SMALL_BOLD,
                width=120,
                height=26,
                fg_color=ACCENT_GREEN,
                hover_color=ACCENT_GREEN_HOVER,
                text_color="#ffffff",
                command=lambda p=repo["path"]: self._convert_repo(p, "ssh"),
            )
            conv_btn.pack(side="right")
        elif proto == "SSH":
            conv_btn = ctk.CTkButton(
                bot_line,
                text="Convert to HTTPS",
                font=FONT_SMALL,
                width=120,
                height=26,
                fg_color=BTN_SECONDARY_BG,
                hover_color=BTN_SECONDARY_HOVER,
                text_color=BTN_SECONDARY_TEXT,
                border_width=1,
                border_color=BORDER_COLOR,
                command=lambda p=repo["path"]: self._convert_repo(p, "https"),
            )
            conv_btn.pack(side="right")

    def _convert_repo(self, repo_path: str, to_protocol: str):
        success, msg = self.manager.app_service.convert_repo_remote(repo_path, to_protocol)
        if success:
            self.on_notify("Remote Updated", msg)
            self.refresh()
        else:
            self.on_notify("Error", msg, is_error=True)

    def _convert_all_to_ssh(self, repos: list):
        converted = 0
        for r in repos:
            if r.get("protocol") == "HTTPS":
                s, _ = self.manager.app_service.convert_repo_remote(r["path"], "ssh")
                if s:
                    converted += 1
        self.on_notify("Bulk Converted", f"Successfully converted {converted} repositories to SSH remotes!")
        self.refresh()