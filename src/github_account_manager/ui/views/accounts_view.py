"""Accounts view displaying configured profiles, PAT auth, public email/user search, and SSH actions."""
import threading
from typing import Callable, Optional
import customtkinter as ctk

from github_account_manager.models import Account
from github_account_manager.services.manager import AccountManager
from github_account_manager.ui.async_runner import run_async
from github_account_manager.ui.components.account_card import AccountCard
from github_account_manager.ui.components.dialogs import (
    AddEditAccountDialog,
    ResultModalDialog,
    SSHTestGuideDialog,
)
from github_account_manager.ui.components.info_banner import InfoBanner
from github_account_manager.ui.theme import (
    ACCENT_GREEN,
    ACCENT_GREEN_HOVER,
    FONT_BODY,
    FONT_HEADING,
    FONT_SUBHEADING,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class AccountsView(ctk.CTkFrame):
    def __init__(self, master, manager: AccountManager, on_notify: Callable[[str, str], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.manager = manager
        self.on_notify = on_notify

        self._build_ui()

    def _build_ui(self):
        # Header Row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(22, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="GitHub Accounts & Profiles",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Manage Git identities, author emails, and SSH keys for each profile.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(3, 0))

        # Add Account Button
        add_btn = ctk.CTkButton(
            header,
            text="+ Add Account",
            font=FONT_BODY,
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=self._open_add_dialog,
            height=36,
        )
        add_btn.pack(side="right")

        # Scrollable Cards Container
        self.cards_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cards_scroll.pack(fill="both", expand=True, padx=25, pady=(10, 20))

        self.refresh()

    def refresh(self):
        # Clear existing card widgets
        for widget in self.cards_scroll.winfo_children():
            widget.destroy()

        # Contextual explanation banner
        InfoBanner(
            self.cards_scroll,
            title="How Account Profiles Work",
            what_it_does="Stores independent Git Author Names, Commit Emails, and SSH Keys for each GitHub profile (e.g. Personal vs Work).",
            why_needed="Prevents your personal email from accidentally appearing in workplace commits and eliminates account confusion across projects.",
            how_it_works="Creates isolated ~/.gitconfig-<profile> files and automatically links them to your project directories via Git includes.",
            icon="👤",
        ).pack(fill="x", pady=(0, 15))

        accounts = self.manager.settings.accounts
        if not accounts:
            empty_box = ctk.CTkFrame(self.cards_scroll, fg_color="transparent")
            empty_box.pack(fill="both", expand=True, pady=60)
            ctk.CTkLabel(
                empty_box,
                text="No accounts configured yet.",
                font=FONT_SUBHEADING,
                text_color=TEXT_MUTED,
            ).pack()
            ctk.CTkLabel(
                empty_box,
                text="Click '+ Add Account' above to set up your personal and work profiles.",
                font=FONT_BODY,
                text_color=TEXT_MUTED,
            ).pack(pady=(4, 0))
            return

        for acc in accounts:
            card = AccountCard(
                self.cards_scroll,
                account=acc,
                on_edit=self._open_edit_dialog,
                on_delete=self._handle_delete,
                on_test_ssh=self._handle_test_ssh,
            )
            card.pack(fill="x", pady=6)

    def _open_add_dialog(self):
        keys = self.manager.ssh_service.list_keys()

        def handle_save(data: dict):
            self.manager.add_account(
                name=data["name"],
                email=data["email"],
                git_name=data["git_name"],
                username=data.get("username", ""),
                ssh_key_path=data.get("ssh_key_path"),
            )
            self.on_notify("Account Created", f"Profile '{data['name']}' has been created.")
            self.refresh()

        def handle_lookup(query: str) -> dict:
            return self.manager.github_service.lookup_user_by_query(query)

        AddEditAccountDialog(
            self.winfo_toplevel(),
            available_keys=keys,
            on_save=handle_save,
            on_lookup=handle_lookup,
        )

    def _open_edit_dialog(self, account: Account):
        keys = self.manager.ssh_service.list_keys()

        def handle_save(data: dict):
            self.manager.update_account(
                account_id=account.id,
                name=data["name"],
                email=data["email"],
                git_name=data["git_name"],
                username=data.get("username"),
                ssh_key_path=data.get("ssh_key_path"),
            )
            self.on_notify("Account Updated", f"Profile '{data['name']}' updated.")
            self.refresh()

        AddEditAccountDialog(
            self.winfo_toplevel(),
            available_keys=keys,
            account=account,
            on_save=handle_save,
        )

    def _handle_delete(self, account: Account):
        self.manager.delete_account(account.id)
        self.on_notify("Account Removed", f"Profile '{account.name}' has been deleted.")
        self.refresh()

    def _handle_test_ssh(self, account: Account):
        if not account.ssh_key_path:
            ResultModalDialog(
                self.winfo_toplevel(),
                title="SSH Test",
                heading="No SSH Key Configured",
                content=f"Account '{account.name}' does not have an SSH key linked yet.\nEdit the profile and select an SSH key.",
                is_success=False,
            )
            return

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
            error_title="SSH Connection Error",
        )