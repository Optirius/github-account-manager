"""SSH Keys management view with dual light/dark mode and clear typography."""
from pathlib import Path
import threading
from typing import Callable, Optional, Tuple
import customtkinter as ctk

from github_account_manager.models import SSHKeyInfo
from github_account_manager.services.manager import AccountManager
from github_account_manager.ui.components.dialogs import (
    BaseDialog,
    ConfirmDeleteDialog,
    NewSSHKeyDialog,
    ResultModalDialog,
    SSHActiveDeleteBlockDialog,
    SSHTestGuideDialog,
)
from github_account_manager.ui.components.status_badge import StatusBadge
from github_account_manager.ui.theme import (
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    ACCENT_GREEN,
    ACCENT_GREEN_HOVER,
    ACCENT_RED,
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
    FONT_SUBHEADING,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class SSHView(ctk.CTkFrame):
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
            text="SSH Keys Manager",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text=f"Manage and generate SSH keys stored in: {self.manager.ssh_service.ssh_dir}",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(3, 0))

        # Actions on right
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        refresh_btn = ctk.CTkButton(
            btn_box,
            text="🔄 Refresh",
            width=95,
            height=36,
            font=FONT_BODY,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self.refresh,
        )
        refresh_btn.pack(side="left", padx=(0, 8))

        gen_btn = ctk.CTkButton(
            btn_box,
            text="+ Generate SSH Key",
            width=160,
            height=36,
            font=FONT_BODY,
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=self._open_generate_dialog,
        )
        gen_btn.pack(side="left")

        # Scrollable Key List
        self.keys_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.keys_scroll.pack(fill="both", expand=True, padx=25, pady=(10, 20))

        self.refresh()

    def refresh(self):
        for widget in self.keys_scroll.winfo_children():
            widget.destroy()

        keys = self.manager.ssh_service.list_keys()

        if not keys:
            empty_box = ctk.CTkFrame(self.keys_scroll, fg_color="transparent")
            empty_box.pack(fill="both", expand=True, pady=60)
            ctk.CTkLabel(
                empty_box,
                text="No SSH keys found in ~/.ssh/",
                font=FONT_SUBHEADING,
                text_color=TEXT_MUTED,
            ).pack()
            ctk.CTkLabel(
                empty_box,
                text="Click '+ Generate SSH Key' above to create one.",
                font=FONT_BODY,
                text_color=TEXT_MUTED,
            ).pack(pady=(4, 0))
            return

        for key_info in keys:
            self._render_key_card(key_info)

    def _render_key_card(self, key_info: SSHKeyInfo):
        card = ctk.CTkFrame(
            self.keys_scroll,
            fg_color=BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.pack(fill="x", pady=6)

        # Header Row
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 4))

        title_lbl = ctk.CTkLabel(
            header,
            text=f"🔑  {key_info.name}",
            font=FONT_SUBHEADING,
            text_color=TEXT_PRIMARY,
        )
        title_lbl.pack(side="left")

        # Key type badge
        StatusBadge(header, key_info.key_type, "info").pack(side="right")

        # Details
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=4)

        if key_info.comment:
            ctk.CTkLabel(
                body,
                text=f"Comment: {key_info.comment}",
                font=FONT_BODY,
                text_color=TEXT_SECONDARY,
            ).pack(anchor="w")

        if key_info.fingerprint:
            ctk.CTkLabel(
                body,
                text=f"Fingerprint: {key_info.fingerprint}",
                font=FONT_MONO_SMALL,
                text_color=TEXT_MUTED,
            ).pack(anchor="w", pady=(2, 0))

        # Public Key Box
        if key_info.public_key_content:
            pub_box = ctk.CTkFrame(card, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
            pub_box.pack(fill="x", padx=16, pady=(6, 12))

            preview = key_info.public_key_content
            if len(preview) > 90:
                preview = preview[:45] + " ... " + preview[-40:]

            ctk.CTkLabel(
                pub_box,
                text=preview,
                font=FONT_MONO_SMALL,
                text_color=TEXT_SECONDARY,
            ).pack(side="left", padx=12, pady=8)

        # Action Buttons
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 14))

        # Copy Public Key button
        if key_info.public_key_content:
            copy_btn = ctk.CTkButton(
                actions,
                text="📋 Copy Public Key",
                width=145,
                height=32,
                font=FONT_SMALL,
                fg_color=BTN_SECONDARY_BG,
                hover_color=BTN_SECONDARY_HOVER,
                text_color=BTN_SECONDARY_TEXT,
                border_width=1,
                border_color=BORDER_COLOR,
                command=lambda k=key_info.public_key_content: self._copy_to_clipboard(k),
            )
            copy_btn.pack(side="left", padx=(0, 8))

        # Test SSH button
        test_btn = ctk.CTkButton(
            actions,
            text="⚡ Test with GitHub",
            width=145,
            height=32,
            font=FONT_SMALL,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=lambda p=key_info.private_key_path, n=key_info.name: self._test_ssh_key(p, n),
        )
        test_btn.pack(side="left", padx=(0, 8))

        # Direct Upload to GitHub button
        auth_accounts = [a for a in self.manager.settings.accounts if a.is_authenticated]
        if auth_accounts and key_info.public_key_content:
            upload_btn = ctk.CTkButton(
                actions,
                text="📤 Upload to GitHub Account...",
                width=195,
                height=32,
                font=FONT_SMALL,
                fg_color=ACCENT_BLUE,
                hover_color=ACCENT_BLUE_HOVER,
                text_color="#ffffff",
                command=lambda k=key_info: self._open_upload_modal(k),
            )
            upload_btn.pack(side="left")

        # Delete SSH key button on far right
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
            command=lambda k=key_info: self._handle_delete_ssh_key(k),
        )
        del_btn.pack(side="right")

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self.on_notify("Copied", "Public SSH key copied to clipboard!")

    def _test_ssh_key(self, priv_path: str, name: str):
        pub_content = self.manager.ssh_service.read_public_key(priv_path) or ""

        def run():
            success, output, user = self.manager.ssh_service.test_connection(priv_path)
            self.after(
                0,
                lambda: SSHTestGuideDialog(
                    self.winfo_toplevel(),
                    key_name=name,
                    public_key_content=pub_content,
                    is_connected=success,
                    output=output,
                    username=user,
                ),
            )

        threading.Thread(target=run, daemon=True).start()

    def _handle_delete_ssh_key(self, key_info: SSHKeyInfo):
        # Test connection live to see if active on GitHub
        self.on_notify("Checking Status", f"Testing if '{key_info.name}' is active on GitHub...")

        def run():
            is_connected, output, user = self.manager.ssh_service.test_connection(key_info.private_key_path)

            if is_connected:
                # Active on GitHub -> block deletion and provide guidance with link
                self.after(
                    0,
                    lambda: SSHActiveDeleteBlockDialog(
                        self.winfo_toplevel(),
                        key_name=key_info.name,
                        username=user,
                    ),
                )
            else:
                # Not active on GitHub -> allow safe deletion
                def confirm_delete():
                    deleted = self.manager.delete_ssh_key(key_info.private_key_path)
                    if deleted:
                        self.on_notify("Key Deleted", f"Deleted SSH key '{key_info.name}' from ~/.ssh/")
                        self.refresh()
                    else:
                        self.on_notify("Error", f"Could not delete '{key_info.name}'.", is_error=True)

                self.after(
                    0,
                    lambda: ConfirmDeleteDialog(
                        self.winfo_toplevel(),
                        title="Delete Unconnected SSH Key",
                        heading=f"Delete '{key_info.name}'?",
                        message=f"SSH test confirms this key is NOT connected to GitHub.\n\n"
                                f"Are you sure you want to permanently delete '{key_info.name}' and its public key from your ~/.ssh/ directory?",
                        on_confirm=confirm_delete,
                    ),
                )

        threading.Thread(target=run, daemon=True).start()

    def _open_generate_dialog(self):
        def handle_gen(data: dict) -> Tuple[bool, str]:
            try:
                priv, pub = self.manager.ssh_service.generate_key(
                    name=data["name"],
                    comment=data["email"],
                    key_type=data["key_type"],
                    passphrase=data.get("passphrase", ""),
                )
                self.after(0, lambda: [
                    self.on_notify("Key Generated", f"Created key pair: {priv.name}"),
                    self.refresh(),
                ])
                return True, f"Created {priv.name}"
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self.on_notify("Error", f"Failed: {err_msg}", is_error=True))
                return False, err_msg

        NewSSHKeyDialog(self.winfo_toplevel(), on_generate=handle_gen)

    def _open_upload_modal(self, key_info: SSHKeyInfo):
        auth_accounts = [a for a in self.manager.settings.accounts if a.is_authenticated]
        if not auth_accounts:
            self.on_notify("No Token", "No accounts are currently logged in with a GitHub token.")
            return

        modal = BaseDialog(self.winfo_toplevel(), "Upload SSH Key to GitHub", 500, 340)
        container = ctk.CTkFrame(modal, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=22, pady=22)

        ctk.CTkLabel(container, text="Select GitHub Account to Upload Key To:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 6))

        options = [f"{a.name} (@{a.username or a.email})" for a in auth_accounts]
        combo = ctk.CTkComboBox(container, values=options, height=36, font=FONT_BODY)
        combo.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(container, text="Key Title on GitHub:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 4))
        title_entry = ctk.CTkEntry(container, placeholder_text="My PC Key", height=36, font=FONT_BODY)
        title_entry.insert(0, f"{key_info.name} ({key_info.key_type})")
        title_entry.pack(fill="x", pady=(0, 20))

        status_lbl = ctk.CTkLabel(container, text="", font=FONT_BODY)
        status_lbl.pack(anchor="w", pady=(0, 10))

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        def submit():
            sel_idx = options.index(combo.get()) if combo.get() in options else 0
            acc = auth_accounts[sel_idx]
            title = title_entry.get().strip()

            def run():
                res = self.manager.upload_ssh_key_to_github(acc.id, key_info.private_key_path, title)
                if res.get("success"):
                    self.after(0, lambda: [modal.destroy(), self.on_notify("Success", f"Key uploaded to GitHub for {acc.name}!")])
                else:
                    self.after(0, lambda: status_lbl.configure(text=f"Error: {res.get('error')}", text_color=ACCENT_RED))

            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=modal.destroy,
            width=90,
            height=36,
        ).pack(side="left")

        ctk.CTkButton(
            btn_row,
            text="Upload Key",
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=submit,
            width=130,
            height=36,
        ).pack(side="right")