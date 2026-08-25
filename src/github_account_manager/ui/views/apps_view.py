"""Universal Apps & Integrations View displaying all auto-discovered Git applications, IDEs, and credentials."""
from pathlib import Path
from typing import Callable, Optional
import customtkinter as ctk

from github_account_manager.services.manager import AccountManager
from github_account_manager.ui.async_runner import run_async
from github_account_manager.ui.components.dialogs import ConfirmDeleteDialog
from github_account_manager.ui.components.info_banner import InfoBanner
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
            text="External Apps & Git Integrations",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Automatically discovered Git clients, IDEs, and Credential Managers on this device.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(3, 0))

        self.refresh_btn = ctk.CTkButton(
            header,
            text="🔄 Scan Apps",
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
        self.refresh_btn.pack(side="right")

        # Scrollable Content
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=25, pady=(10, 20))

        self.refresh()

    def refresh(self):
        def task():
            apps = self.manager.app_service.detect_all_installed_apps()
            creds = self.manager.app_service.list_windows_git_credentials()
            repos = self.manager.app_service.scan_repositories(self.manager.settings.folder_mappings)
            ide_accounts = self.manager.app_service.get_ide_github_accounts()
            return apps, creds, repos, ide_accounts

        def on_done(data):
            apps, creds, repos, ide_accounts = data
            for widget in self.scroll.winfo_children():
                widget.destroy()

            # Contextual explanation banner
            InfoBanner(
                self.scroll,
                title="How App & IDE Isolation Works",
                what_it_does="Discovers external code editors (VS Code, Visual Studio, JetBrains Rider, etc.), clears cached Windows credentials, and converts repo remotes to dedicated SSH aliases.",
                why_needed="IDEs and Windows Credential Manager inject global credentials that override local folder rules and cause 'Permission Denied' errors.",
                how_it_works="Disables built-in IDE Git authentication and switches repository remotes to dedicated SSH host aliases so every tool respects your directory profile.",
                icon="🧩",
            ).pack(fill="x", pady=(0, 15))

            if ide_accounts:
                self._render_ide_accounts_section(ide_accounts)

            self._render_detected_apps_section(apps)
            self._render_credentials_section(creds)
            self._render_repo_converter_section(repos)

        run_async(
            self,
            task_fn=task,
            on_success=on_done,
            loading_btn=self.refresh_btn,
            loading_text="⏳ Scanning...",
            error_title="App Scan Error",
        )

    # --- Section 0: IDE Configured GitHub Accounts ---

    def _render_ide_accounts_section(self, ide_accounts: list):
        card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(0, 16))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            header,
            text=f"🔑  IDE Configured GitHub Accounts ({len(ide_accounts)} detected)",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(
            body,
            text="GitHub accounts logged in directly inside external IDE settings (e.g. JetBrains Rider, IntelliJ IDEA, PyCharm).\n"
                 "To ensure Git pushes use your directory-mapped profile, verify your repositories use SSH remotes.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        for acc in ide_accounts:
            row = ctk.CTkFrame(body, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
            row.pack(fill="x", pady=3)

            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=8)

            ctk.CTkLabel(
                top,
                text=f"👤  {acc['account']}",
                font=FONT_BODY_BOLD,
                text_color=TEXT_PRIMARY,
            ).pack(side="left")

            StatusBadge(top, acc["source"], "info").pack(side="right")

    # --- Section 1: Auto-Discovered Applications ---

    def _render_detected_apps_section(self, apps: list):
        ide_apps = [a for a in apps if a.get("supports_isolation")]
        needs_isolation = [a for a in ide_apps if not a.get("is_isolated")]

        card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(0, 16))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            header,
            text=f"🖥️  Auto-Discovered Git Applications ({len(apps)} found on device)",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        if needs_isolation:
            bulk_btn = ctk.CTkButton(
                header,
                text="⚡ Apply Isolation to All IDEs",
                font=FONT_BODY_BOLD,
                height=32,
                fg_color=ACCENT_GREEN,
                hover_color=ACCENT_GREEN_HOVER,
                text_color="#ffffff",
            )
            bulk_btn.configure(command=lambda b=bulk_btn: self._apply_isolation_to_all(b))
            bulk_btn.pack(side="right")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(
            body,
            text="The manager scans your system for code editors, Git GUI clients, and credential helpers.\n"
                 "IDEs with built-in GitHub accounts can be isolated with one click to enforce folder-specific accounts.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        for app in apps:
            self._render_app_row(body, app)

    def _render_app_row(self, parent, app: dict):
        row = ctk.CTkFrame(parent, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
        row.pack(fill="x", pady=4)

        top_line = ctk.CTkFrame(row, fg_color="transparent")
        top_line.pack(fill="x", padx=14, pady=(10, 2))

        title_box = ctk.CTkFrame(top_line, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text=f"{app['icon']}  {app['name']}",
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        # Status badge
        StatusBadge(top_line, app["status_badge"], app["badge_variant"]).pack(side="right")

        # Description
        mid_line = ctk.CTkFrame(row, fg_color="transparent")
        mid_line.pack(fill="x", padx=14, pady=(2, 6))

        ctk.CTkLabel(
            mid_line,
            text=app["description"],
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
            justify="left",
            wraplength=700,
        ).pack(anchor="w")

        # Action Buttons
        if app.get("supports_isolation"):
            bot_line = ctk.CTkFrame(row, fg_color="transparent")
            bot_line.pack(fill="x", padx=14, pady=(0, 10))

            if not app.get("is_isolated"):
                iso_btn = ctk.CTkButton(
                    bot_line,
                    text=f"⚡ Enable Folder Isolation in {app['name']}",
                    font=FONT_SMALL_BOLD,
                    height=28,
                    fg_color=ACCENT_GREEN,
                    hover_color=ACCENT_GREEN_HOVER,
                    text_color="#ffffff",
                )
                iso_btn.configure(command=lambda i=app["id"], b=iso_btn: self._apply_app_isolation(i, b))
                iso_btn.pack(side="left", padx=(0, 8))
            else:
                rst_btn = ctk.CTkButton(
                    bot_line,
                    text="↩️ Restore Defaults",
                    font=FONT_SMALL,
                    height=28,
                    fg_color=BTN_SECONDARY_BG,
                    hover_color=BTN_SECONDARY_HOVER,
                    text_color=BTN_SECONDARY_TEXT,
                    border_width=1,
                    border_color=BORDER_COLOR,
                )
                rst_btn.configure(command=lambda i=app["id"], b=rst_btn: self._restore_app_defaults(i, b))
                rst_btn.pack(side="left")

    def _apply_app_isolation(self, app_id: str, btn: Optional[ctk.CTkButton] = None):
        def task():
            return self.manager.app_service.apply_isolation_to_app(app_id)

        def on_done(res):
            success, msg = res
            if success:
                self.on_notify("Configured", msg)
                self.refresh()
            else:
                self.on_notify("Error", msg, is_error=True)

        run_async(
            self,
            task_fn=task,
            on_success=on_done,
            loading_btn=btn,
            loading_text="⏳ Applying...",
            error_title="IDE Configuration Error",
        )

    def _apply_isolation_to_all(self, btn: Optional[ctk.CTkButton] = None):
        def task():
            return self.manager.app_service.apply_isolation_to_all_ides()

        def on_done(res):
            count, msgs = res
            self.on_notify("IDEs Configured", f"Successfully applied folder isolation to {count} IDEs!")
            self.refresh()

        run_async(
            self,
            task_fn=task,
            on_success=on_done,
            loading_btn=btn,
            loading_text="⏳ Applying to All...",
            error_title="IDE Bulk Isolation Error",
        )

    def _restore_app_defaults(self, app_id: str, btn: Optional[ctk.CTkButton] = None):
        def task():
            return self.manager.app_service.restore_defaults_for_app(app_id)

        def on_done(res):
            success, msg = res
            if success:
                self.on_notify("Restored", msg)
                self.refresh()
            else:
                self.on_notify("Error", msg, is_error=True)

        run_async(
            self,
            task_fn=task,
            on_success=on_done,
            loading_btn=btn,
            loading_text="⏳ Restoring...",
            error_title="Restore Defaults Error",
        )

    # --- Section 2: Windows Git Credential Manager (GCM) ---

    def _render_credentials_section(self, creds: list):
        card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(0, 16))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            header,
            text="🔐  Windows Credential Vault (Git & GitHub)",
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
                )
                del_btn.configure(command=lambda t=target, u=user, b=del_btn: self._delete_credential(t, u, b))
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

    def _delete_credential(self, target: str, user: str, btn: Optional[ctk.CTkButton] = None):
        def confirm():
            def task():
                return self.manager.app_service.delete_windows_credential(target)

            def on_done(res):
                success, msg = res
                if success:
                    self.on_notify("Credential Cleared", f"Cleared cached credential for @{user}.")
                    self.refresh()
                else:
                    self.on_notify("Error", msg, is_error=True)

            run_async(
                self,
                task_fn=task,
                on_success=on_done,
                loading_btn=btn,
                loading_text="⏳ Clearing...",
                error_title="Credential Clear Error",
            )

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
        def task():
            return self.manager.app_service.enable_git_credential_use_http_path()

        def on_done(res):
            success, msg = res
            if success:
                self.on_notify("Configured", msg)
            else:
                self.on_notify("Error", msg, is_error=True)

        run_async(self, task_fn=task, on_success=on_done, error_title="Git Config Error")

    # --- Section 3: Repository Remote Converter (HTTPS -> SSH) ---

    def _render_repo_converter_section(self, repos: list):
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
            )
            bulk_btn.configure(command=lambda b=bulk_btn: self._convert_all_to_ssh(repos, b))
            bulk_btn.pack(side="right")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(
            body,
            text="SSH host aliases (e.g. git@github-personal:owner/repo.git) are 100% immune to IDE credential hijacking.\n"
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

        acc = next((a for a in self.manager.settings.accounts if a.id == repo["account_id"]), None)
        acc_label = f"Assigned: {acc.name}" if acc else "Assigned Account"

        ctk.CTkLabel(
            top_line,
            text=f"({acc_label})",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=8)

        proto = repo.get("protocol", "Local")
        badge_variant = "active" if proto == "SSH" else ("warning" if proto == "HTTPS" else "neutral")
        badge_text = "SSH (Safe & Isolated ✓)" if proto == "SSH" else ("HTTPS (Hijack Risk ⚠️)" if proto == "HTTPS" else proto)
        StatusBadge(top_line, badge_text, badge_variant).pack(side="right")

        bot_line = ctk.CTkFrame(row, fg_color="transparent")
        bot_line.pack(fill="x", padx=12, pady=(2, 8))

        ctk.CTkLabel(
            bot_line,
            text=repo.get("remote_url") or "(no origin remote)",
            font=FONT_MONO_SMALL,
            text_color=TEXT_SECONDARY,
        ).pack(side="left")

        account_slug = acc.name.lower().replace(" ", "-") if acc else None

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
            )
            conv_btn.configure(command=lambda p=repo["path"], s=account_slug, b=conv_btn: self._convert_repo(p, "ssh", s, b))
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
            )
            conv_btn.configure(command=lambda p=repo["path"], b=conv_btn: self._convert_repo(p, "https", None, b))
            conv_btn.pack(side="right")

    def _convert_repo(self, repo_path: str, to_protocol: str, account_slug: Optional[str] = None, btn: Optional[ctk.CTkButton] = None):
        def task():
            return self.manager.app_service.convert_repo_remote(repo_path, to_protocol, account_slug)

        def on_done(res):
            success, msg = res
            if success:
                self.on_notify("Remote Updated", msg)
                self.refresh()
            else:
                self.on_notify("Error", msg, is_error=True)

        run_async(
            self,
            task_fn=task,
            on_success=on_done,
            loading_btn=btn,
            loading_text="⏳",
            error_title="Remote Conversion Error",
        )

    def _convert_all_to_ssh(self, repos: list, btn: Optional[ctk.CTkButton] = None):
        def task():
            converted = 0
            for r in repos:
                if r.get("protocol") == "HTTPS":
                    acc = next((a for a in self.manager.settings.accounts if a.id == r.get("account_id")), None)
                    slug = acc.name.lower().replace(" ", "-") if acc else None
                    s, _ = self.manager.app_service.convert_repo_remote(r["path"], "ssh", slug)
                    if s:
                        converted += 1
            return converted

        def on_done(converted):
            self.on_notify("Bulk Converted", f"Successfully converted {converted} repositories to SSH remotes!")
            self.refresh()

        run_async(
            self,
            task_fn=task,
            on_success=on_done,
            loading_btn=btn,
            loading_text="⏳ Converting All...",
            error_title="Bulk Conversion Error",
        )