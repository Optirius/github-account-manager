"""Modal dialogs with full light and dark mode styling, crisp fonts, and email/username/token lookup."""
from pathlib import Path
import threading
import tkinter.filedialog as fd
import webbrowser
from typing import Callable, List, Optional, Tuple
import customtkinter as ctk

from github_account_manager.config import DEFAULT_SSH_DIR, GITHUB_NEW_TOKEN_URL
from github_account_manager.models import Account, SSHKeyInfo
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
    FONT_SUBHEADING,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class BaseDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, width: int = 560, height: int = 600):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.configure(fg_color=BG_APP)
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{max(0, x)}+{max(0, y)}")


class TokenLoginDialog(BaseDialog):
    def __init__(self, parent, account_name: str, on_login: Callable[[str], None]):
        super().__init__(parent, f"GitHub Login - {account_name}", 560, 430)
        self.on_login = on_login

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=25)

        title_lbl = ctk.CTkLabel(
            container,
            text=f"Authenticate '{account_name}'",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        )
        title_lbl.pack(anchor="w", pady=(0, 8))

        desc_lbl = ctk.CTkLabel(
            container,
            text="Enter a GitHub Personal Access Token (classic or fine-grained).\n"
                 "Tokens are stored securely in Windows Credential Manager.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            justify="left",
        )
        desc_lbl.pack(anchor="w", pady=(0, 15))

        ctk.CTkLabel(container, text="Personal Access Token (PAT):", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 4))
        self.token_entry = ctk.CTkEntry(
            container,
            placeholder_text="ghp_xxxxxxxxxxxxxxxxxxxx",
            show="*",
            font=FONT_MONO,
            height=38,
        )
        self.token_entry.pack(fill="x", pady=(0, 10))

        def open_token_url():
            webbrowser.open_new_tab(GITHUB_NEW_TOKEN_URL)

        gen_btn = ctk.CTkButton(
            container,
            text="🔗 Open GitHub to Generate Token (Pre-configured scopes)",
            fg_color=BTN_SECONDARY_BG,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=ACCENT_BLUE,
            hover_color=BTN_SECONDARY_HOVER,
            command=open_token_url,
            height=34,
            font=FONT_SMALL,
        )
        gen_btn.pack(fill="x", pady=(0, 15))

        self.status_lbl = ctk.CTkLabel(container, text="", font=FONT_BODY, text_color=TEXT_MUTED)
        self.status_lbl.pack(anchor="w", pady=(0, 10))

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self.destroy,
            width=100,
            height=36,
            font=FONT_BODY,
        )
        cancel_btn.pack(side="left")

        self.submit_btn = ctk.CTkButton(
            btn_row,
            text="Verify & Login",
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=self._handle_submit,
            width=140,
            height=36,
            font=FONT_BODY_BOLD,
        )
        self.submit_btn.pack(side="right")

    def _handle_submit(self):
        token = self.token_entry.get().strip()
        if not token:
            self.status_lbl.configure(text="Please enter a token.", text_color=ACCENT_RED)
            return

        self.status_lbl.configure(text="Validating token with GitHub API...", text_color=ACCENT_BLUE)
        self.submit_btn.configure(state="disabled")
        self.on_login(token)


class AddEditAccountDialog(BaseDialog):
    def __init__(
        self,
        parent,
        available_keys: List[SSHKeyInfo],
        account: Optional[Account] = None,
        on_save: Optional[Callable[[dict], None]] = None,
        on_lookup: Optional[Callable[[str], dict]] = None,
    ):
        title = "Edit Account Profile" if account else "Add GitHub Account Profile"
        super().__init__(parent, title, 580, 710)
        self.account = account
        self.available_keys = available_keys
        self.on_save = on_save
        self.on_lookup = on_lookup

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=22, pady=22)

        # Title
        ctk.CTkLabel(
            scroll,
            text=title,
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 12))

        # Quick Search / Autofill Section (Email, Username, or Token)
        if not account:
            autofill_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
            autofill_card.pack(fill="x", pady=(0, 15), padx=2)

            ctk.CTkLabel(
                autofill_card,
                text="⚡ Search & Auto-Fill Profile from GitHub",
                font=FONT_SUBHEADING,
                text_color=TEXT_PRIMARY,
            ).pack(anchor="w", padx=16, pady=(12, 4))

            ctk.CTkLabel(
                autofill_card,
                text="Enter an Email, GitHub Username (@handle), or Personal Access Token.",
                font=FONT_SMALL,
                text_color=TEXT_SECONDARY,
            ).pack(anchor="w", padx=16, pady=(0, 10))

            search_row = ctk.CTkFrame(autofill_card, fg_color="transparent")
            search_row.pack(fill="x", padx=16, pady=(0, 14))

            self.search_entry = ctk.CTkEntry(
                search_row,
                placeholder_text="e.g. user@gmail.com, octocat, or ghp_...",
                font=FONT_BODY,
                height=36,
            )
            self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self.search_entry.bind("<Return>", lambda e: self._handle_lookup())

            self.search_btn = ctk.CTkButton(
                search_row,
                text="🔍 Search & Fill",
                width=125,
                height=36,
                font=FONT_BODY_BOLD,
                fg_color=ACCENT_BLUE,
                hover_color=ACCENT_BLUE_HOVER,
                text_color="#ffffff",
                command=self._handle_lookup,
            )
            self.search_btn.pack(side="right")

        # Account Name / Label
        ctk.CTkLabel(scroll, text="Profile Label (e.g. Personal, Work, Selise):", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 3))
        self.name_entry = ctk.CTkEntry(scroll, placeholder_text="Personal", height=36, font=FONT_BODY)
        self.name_entry.pack(fill="x", pady=(0, 12))
        if account:
            self.name_entry.insert(0, account.name)

        # Git Commit Author Name
        ctk.CTkLabel(scroll, text="Git Author Name (user.name):", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 3))
        self.git_name_entry = ctk.CTkEntry(scroll, placeholder_text="Tahmid Hossain", height=36, font=FONT_BODY)
        self.git_name_entry.pack(fill="x", pady=(0, 12))
        if account:
            self.git_name_entry.insert(0, account.git_name)

        # Git Commit Email
        ctk.CTkLabel(scroll, text="Git Commit Email (user.email):", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 3))
        self.email_entry = ctk.CTkEntry(scroll, placeholder_text="name@example.com", height=36, font=FONT_BODY)
        self.email_entry.pack(fill="x", pady=(0, 12))
        if account:
            self.email_entry.insert(0, account.email)

        # GitHub Username
        ctk.CTkLabel(scroll, text="GitHub Username (handle):", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 3))
        self.username_entry = ctk.CTkEntry(scroll, placeholder_text="octocat", height=36, font=FONT_BODY)
        self.username_entry.pack(fill="x", pady=(0, 12))
        if account:
            self.username_entry.insert(0, account.username)

        # SSH Key Selection
        ctk.CTkLabel(scroll, text="SSH Key (for push / pull operations):", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 3))
        ssh_row = ctk.CTkFrame(scroll, fg_color="transparent")
        ssh_row.pack(fill="x", pady=(0, 16))

        key_options = ["None"] + [k.name for k in available_keys]
        self.ssh_combo = ctk.CTkComboBox(
            ssh_row,
            values=key_options,
            height=36,
            font=FONT_BODY,
        )
        self.ssh_combo.pack(side="left", fill="x", expand=True, padx=(0, 8))

        if account and account.ssh_key_path:
            p_name = Path(account.ssh_key_path).name
            if p_name in key_options:
                self.ssh_combo.set(p_name)
            else:
                self.ssh_combo.set(account.ssh_key_path)
        else:
            self.ssh_combo.set("None")

        browse_key_btn = ctk.CTkButton(
            ssh_row,
            text="Browse...",
            width=85,
            height=36,
            font=FONT_SMALL,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self._browse_custom_key,
        )
        browse_key_btn.pack(side="right")

        self.status_lbl = ctk.CTkLabel(scroll, text="", font=FONT_BODY, text_color=ACCENT_RED)
        self.status_lbl.pack(anchor="w", pady=(0, 10))

        # Bottom buttons
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self.destroy,
            width=100,
            height=36,
            font=FONT_BODY,
        )
        cancel_btn.pack(side="left")

        save_btn = ctk.CTkButton(
            btn_row,
            text="Save Account",
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=self._handle_save,
            width=140,
            height=36,
            font=FONT_BODY_BOLD,
        )
        save_btn.pack(side="right")

    def _browse_custom_key(self):
        filename = fd.askopenfilename(
            title="Select SSH Private Key",
            initialdir=str(DEFAULT_SSH_DIR),
        )
        if filename:
            self.ssh_combo.set(filename)

    def _handle_lookup(self):
        query = getattr(self, "search_entry", None)
        if not query:
            return
        q_str = query.get().strip()
        if not q_str:
            self.status_lbl.configure(text="Please enter an email, username, or token to search.", text_color=ACCENT_RED)
            return

        self.status_lbl.configure(text="Searching GitHub for account info...", text_color=ACCENT_BLUE)
        self.search_btn.configure(state="disabled")

        def run():
            if self.on_lookup:
                res = self.on_lookup(q_str)
                self.after(0, lambda: self._apply_lookup_result(q_str, res))

        threading.Thread(target=run, daemon=True).start()

    def _apply_lookup_result(self, query: str, res: dict):
        self.search_btn.configure(state="normal")
        if res.get("success"):
            if res.get("username"):
                self.username_entry.delete(0, "end")
                self.username_entry.insert(0, res["username"])

            if res.get("name"):
                self.git_name_entry.delete(0, "end")
                self.git_name_entry.insert(0, res["name"])

            if res.get("email"):
                self.email_entry.delete(0, "end")
                self.email_entry.insert(0, res["email"])
            elif "@" in query:
                self.email_entry.delete(0, "end")
                self.email_entry.insert(0, query)

            if not self.name_entry.get():
                candidate_label = res.get("name") or res.get("username") or (query.split("@")[0].capitalize() if "@" in query else query)
                self.name_entry.delete(0, "end")
                self.name_entry.insert(0, candidate_label)

            matched_key = self._find_matching_ssh_key(res.get("username", ""), res.get("email", "") or query)
            if matched_key:
                self.ssh_combo.set(matched_key.name)

            if res.get("token"):
                self._token_to_save = res["token"]

            msg = f"✓ Found GitHub profile: @{res.get('username') or res.get('name')}"
            self.status_lbl.configure(text=msg, text_color=ACCENT_GREEN)
        else:
            self.status_lbl.configure(text=f"Lookup failed: {res.get('error')}", text_color=ACCENT_RED)

    def _find_matching_ssh_key(self, username: str, email: str) -> Optional[SSHKeyInfo]:
        """Auto-match an SSH key from ~/.ssh/ by email or username in key comment or filename."""
        u_lower = username.lower() if username else ""
        e_lower = email.lower() if email else ""

        for key in self.available_keys:
            k_name = key.name.lower()
            k_comm = (key.comment or "").lower()
            if e_lower and (e_lower in k_comm or e_lower.split("@")[0] in k_name):
                return key
            if u_lower and (u_lower in k_name or u_lower in k_comm):
                return key
        return None

    def _handle_save(self):
        name = self.name_entry.get().strip()
        git_name = self.git_name_entry.get().strip()
        email = self.email_entry.get().strip()
        username = self.username_entry.get().strip()
        selected_key = self.ssh_combo.get().strip()

        if not name:
            self.status_lbl.configure(text="Please provide a profile name (e.g. Personal).", text_color=ACCENT_RED)
            return
        if not git_name:
            self.status_lbl.configure(text="Please provide a Git Author Name.", text_color=ACCENT_RED)
            return
        if not email:
            self.status_lbl.configure(text="Please provide a Git Commit Email.", text_color=ACCENT_RED)
            return

        ssh_key_path = None
        if selected_key and selected_key != "None":
            matching = next((k for k in self.available_keys if k.name == selected_key), None)
            if matching:
                ssh_key_path = matching.private_key_path
            else:
                ssh_key_path = selected_key

        token = getattr(self, "_token_to_save", None)
        search_field = getattr(self, "search_entry", None)
        if not token and search_field:
            s_val = search_field.get().strip()
            if s_val.startswith("ghp_") or s_val.startswith("github_pat_"):
                token = s_val

        data = {
            "name": name,
            "git_name": git_name,
            "email": email,
            "username": username,
            "ssh_key_path": ssh_key_path,
            "token": token,
        }

        if self.on_save:
            self.on_save(data)
        self.destroy()


class NewSSHKeyDialog(BaseDialog):
    def __init__(
        self,
        parent,
        default_email: str = "",
        default_name: str = "",
        on_generate: Optional[Callable[[dict], Tuple[bool, str]]] = None,
    ):
        super().__init__(parent, "Generate New SSH Key", 560, 540)
        self.on_generate = on_generate

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=25)

        ctk.CTkLabel(container, text="Generate SSH Key Pair", font=FONT_HEADING, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 12))

        # Key Name
        ctk.CTkLabel(container, text="Key Filename (saved in ~/.ssh/):", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 3))
        self.key_name_entry = ctk.CTkEntry(container, height=36, font=FONT_BODY)
        self.key_name_entry.pack(fill="x", pady=(0, 12))
        
        # Pre-fill actual text
        initial_name = f"id_ed25519_{default_name.lower()}" if default_name else "id_ed25519_custom"
        self.key_name_entry.insert(0, initial_name)

        # Email / Comment
        ctk.CTkLabel(container, text="Email / Key Comment:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 3))
        self.email_entry = ctk.CTkEntry(container, placeholder_text="user@example.com", height=36, font=FONT_BODY)
        self.email_entry.pack(fill="x", pady=(0, 12))
        if default_email:
            self.email_entry.insert(0, default_email)

        # Key Algorithm
        ctk.CTkLabel(container, text="Key Algorithm:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 3))
        self.algo_combo = ctk.CTkComboBox(
            container,
            values=["ED25519 (Recommended, Modern & Fast)", "RSA (4096-bit, Legacy)"],
            height=36,
            font=FONT_BODY,
        )
        self.algo_combo.pack(fill="x", pady=(0, 12))

        # Passphrase (optional)
        ctk.CTkLabel(container, text="Passphrase (Optional - leave empty for none):", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 3))
        self.passphrase_entry = ctk.CTkEntry(container, placeholder_text="Optional passphrase", show="*", height=36, font=FONT_BODY)
        self.passphrase_entry.pack(fill="x", pady=(0, 15))

        self.status_lbl = ctk.CTkLabel(container, text="", font=FONT_BODY, text_color=ACCENT_RED, wraplength=480, justify="left")
        self.status_lbl.pack(anchor="w", pady=(0, 10))

        # Bottom buttons
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self.destroy,
            width=100,
            height=36,
            font=FONT_BODY,
        )
        cancel_btn.pack(side="left")

        self.gen_btn = ctk.CTkButton(
            btn_row,
            text="Generate Key",
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=self._handle_generate,
            width=140,
            height=36,
            font=FONT_BODY_BOLD,
        )
        self.gen_btn.pack(side="right")

    def _handle_generate(self):
        name = self.key_name_entry.get().strip()
        email = self.email_entry.get().strip()
        algo_choice = self.algo_combo.get()
        passphrase = self.passphrase_entry.get()

        if not name:
            self.status_lbl.configure(text="Please provide a key name.", text_color=ACCENT_RED)
            return

        key_type = "ed25519" if "ED25519" in algo_choice else "rsa"
        data = {
            "name": name,
            "email": email,
            "key_type": key_type,
            "passphrase": passphrase,
        }

        self.status_lbl.configure(text="Generating key pair in background...", text_color=ACCENT_BLUE)
        self.gen_btn.configure(state="disabled")

        def run():
            if self.on_generate:
                success, msg = self.on_generate(data)
                self.after(0, lambda: self._on_generate_done(success, msg))

        threading.Thread(target=run, daemon=True).start()

    def _on_generate_done(self, success: bool, msg: str):
        self.gen_btn.configure(state="normal")
        if success:
            self.destroy()
        else:
            self.status_lbl.configure(text=f"Error: {msg}", text_color=ACCENT_RED)


class AddFolderMappingDialog(BaseDialog):
    def __init__(
        self,
        parent,
        accounts: List[Account],
        on_add: Callable[[str, str], None],
    ):
        super().__init__(parent, "Map Directory to Account", 560, 400)
        self.accounts = accounts
        self.on_add = on_add

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=25)

        ctk.CTkLabel(
            container,
            text="Map Directory to Account",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(
            container,
            text="All repositories inside this folder will automatically use the selected account.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 15))

        # Folder path picker
        ctk.CTkLabel(container, text="Target Directory Path:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 3))
        folder_row = ctk.CTkFrame(container, fg_color="transparent")
        folder_row.pack(fill="x", pady=(0, 14))

        self.path_entry = ctk.CTkEntry(folder_row, placeholder_text="D:/Personal or D:/Professional", height=36, font=FONT_BODY)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ctk.CTkButton(
            folder_row,
            text="Browse...",
            width=90,
            height=36,
            font=FONT_SMALL,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self._browse_dir,
        )
        browse_btn.pack(side="right")

        # Select Account
        ctk.CTkLabel(container, text="Assign to GitHub Account:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(5, 3))
        acc_options = [f"{a.name} ({a.email})" for a in accounts]
        self.acc_combo = ctk.CTkComboBox(
            container,
            values=acc_options if acc_options else ["No accounts created"],
            height=36,
            font=FONT_BODY,
        )
        self.acc_combo.pack(fill="x", pady=(0, 15))

        self.status_lbl = ctk.CTkLabel(container, text="", font=FONT_BODY, text_color=ACCENT_RED)
        self.status_lbl.pack(anchor="w", pady=(0, 10))

        # Bottom buttons
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self.destroy,
            width=100,
            height=36,
            font=FONT_BODY,
        )
        cancel_btn.pack(side="left")

        save_btn = ctk.CTkButton(
            btn_row,
            text="Create Mapping",
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            text_color="#ffffff",
            command=self._handle_save,
            width=140,
            height=36,
            font=FONT_BODY_BOLD,
        )
        save_btn.pack(side="right")

    def _browse_dir(self):
        chosen = fd.askdirectory(title="Select Folder to Map")
        if chosen:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, chosen)

    def _handle_save(self):
        folder = self.path_entry.get().strip()
        selected_acc_str = self.acc_combo.get()

        if not folder:
            self.status_lbl.configure(text="Please select or enter a directory path.")
            return

        if not self.accounts:
            self.status_lbl.configure(text="Please create an account first.")
            return

        acc_index = self.acc_combo._values.index(selected_acc_str) if selected_acc_str in self.acc_combo._values else 0
        account = self.accounts[acc_index]

        self.on_add(folder, account.id)
        self.destroy()


class ResultModalDialog(BaseDialog):
    def __init__(self, parent, title: str, heading: str, content: str, is_success: bool = True):
        super().__init__(parent, title, 600, 440)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=25)

        color = ACCENT_GREEN if is_success else ACCENT_RED
        icon = "✓ " if is_success else "✗ "

        ctk.CTkLabel(
            container,
            text=f"{icon}{heading}",
            font=FONT_HEADING,
            text_color=color,
        ).pack(anchor="w", pady=(0, 14))

        # Text box for output
        text_box = ctk.CTkTextbox(
            container,
            font=FONT_MONO,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
            wrap="word",
        )
        text_box.pack(fill="both", expand=True, pady=(0, 15))
        text_box.insert("1.0", content)
        text_box.configure(state="disabled")

        close_btn = ctk.CTkButton(
            container,
            text="Close",
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self.destroy,
            width=110,
            height=36,
            font=FONT_BODY,
        )
        close_btn.pack(side="right")


class SSHTestGuideDialog(BaseDialog):
    """Rich interactive test result dialog with in-app step-by-step guidance."""
    def __init__(
        self,
        parent,
        key_name: str,
        public_key_content: str,
        is_connected: bool,
        output: str,
        username: Optional[str] = None,
    ):
        super().__init__(parent, f"SSH Test Result - {key_name}", 660, 560)
        self.public_key_content = public_key_content
        self.ssh_settings_url = "https://github.com/settings/keys"

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=22)

        if is_connected:
            ctk.CTkLabel(
                container,
                text=f"✓  Connected as @{username or 'GitHub User'}",
                font=FONT_HEADING,
                text_color=ACCENT_GREEN,
            ).pack(anchor="w", pady=(0, 6))

            ctk.CTkLabel(
                container,
                text="This SSH key is active and successfully authenticated with GitHub.",
                font=FONT_BODY,
                text_color=TEXT_SECONDARY,
            ).pack(anchor="w", pady=(0, 12))

            text_box = ctk.CTkTextbox(
                container,
                font=FONT_MONO,
                fg_color=BG_CARD,
                border_width=1,
                border_color=BORDER_COLOR,
                text_color=TEXT_PRIMARY,
                height=220,
                wrap="word",
            )
            text_box.pack(fill="both", expand=True, pady=(0, 16))
            text_box.insert("1.0", output)
            text_box.configure(state="disabled")

            btn_row = ctk.CTkFrame(container, fg_color="transparent")
            btn_row.pack(fill="x", side="bottom")

            ctk.CTkButton(
                btn_row,
                text="Close",
                fg_color=BTN_SECONDARY_BG,
                hover_color=BTN_SECONDARY_HOVER,
                text_color=BTN_SECONDARY_TEXT,
                border_width=1,
                border_color=BORDER_COLOR,
                command=self.destroy,
                width=110,
                height=36,
                font=FONT_BODY,
            ).pack(side="right")

        else:
            ctk.CTkLabel(
                container,
                text="⚠️  SSH Key Not Registered on GitHub",
                font=FONT_HEADING,
                text_color=ACCENT_RED,
            ).pack(anchor="w", pady=(0, 4))

            ctk.CTkLabel(
                container,
                text="GitHub rejected the connection because this public key has not been added to your account yet.",
                font=FONT_BODY,
                text_color=TEXT_SECONDARY,
            ).pack(anchor="w", pady=(0, 14))

            guide_card = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
            guide_card.pack(fill="both", expand=True, pady=(0, 14))

            ctk.CTkLabel(
                guide_card,
                text="📖 How to Add this SSH Key to GitHub:",
                font=FONT_SUBHEADING,
                text_color=TEXT_PRIMARY,
            ).pack(anchor="w", padx=16, pady=(12, 8))

            # Step 1
            s1 = ctk.CTkFrame(guide_card, fg_color="transparent")
            s1.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(s1, text="1.", font=FONT_BODY_BOLD, text_color=ACCENT_BLUE, width=18).pack(side="left")
            ctk.CTkLabel(s1, text="Copy your public SSH key to clipboard:", font=FONT_BODY, text_color=TEXT_PRIMARY).pack(side="left")

            if self.public_key_content:
                self.copy_key_btn = ctk.CTkButton(
                    s1,
                    text="📋 Copy Key",
                    width=100,
                    height=28,
                    font=FONT_SMALL,
                    fg_color=BTN_SECONDARY_BG,
                    hover_color=BTN_SECONDARY_HOVER,
                    text_color=BTN_SECONDARY_TEXT,
                    border_width=1,
                    border_color=BORDER_COLOR,
                    command=self._copy_key,
                )
                self.copy_key_btn.pack(side="right")

            # Step 2: Link
            s2 = ctk.CTkFrame(guide_card, fg_color="transparent")
            s2.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(s2, text="2.", font=FONT_BODY_BOLD, text_color=ACCENT_BLUE, width=18).pack(side="left")
            ctk.CTkLabel(s2, text="Go to GitHub SSH Keys Settings:", font=FONT_BODY, text_color=TEXT_PRIMARY).pack(side="left")

            link_box = ctk.CTkFrame(guide_card, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
            link_box.pack(fill="x", padx=34, pady=(2, 6))

            ctk.CTkLabel(
                link_box,
                text=self.ssh_settings_url,
                font=FONT_MONO_SMALL,
                text_color=ACCENT_BLUE,
            ).pack(side="left", padx=10, pady=6)

            self.copy_link_btn = ctk.CTkButton(
                link_box,
                text="📋 Copy Link",
                width=90,
                height=26,
                font=FONT_SMALL,
                fg_color=BTN_SECONDARY_BG,
                hover_color=BTN_SECONDARY_HOVER,
                text_color=BTN_SECONDARY_TEXT,
                command=self._copy_url,
            )
            self.copy_link_btn.pack(side="right", padx=6, pady=4)

            # Step 3
            s3 = ctk.CTkFrame(guide_card, fg_color="transparent")
            s3.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(s3, text="3.", font=FONT_BODY_BOLD, text_color=ACCENT_BLUE, width=18).pack(side="left")
            ctk.CTkLabel(s3, text="Click 'New SSH key', paste the key into 'Key', and click 'Add SSH key'.", font=FONT_BODY, text_color=TEXT_PRIMARY).pack(side="left")

            # Step 4
            s4 = ctk.CTkFrame(guide_card, fg_color="transparent")
            s4.pack(fill="x", padx=16, pady=(3, 12))
            ctk.CTkLabel(s4, text="4.", font=FONT_BODY_BOLD, text_color=ACCENT_BLUE, width=18).pack(side="left")
            ctk.CTkLabel(s4, text="Return to this app and test the connection again.", font=FONT_BODY, text_color=TEXT_PRIMARY).pack(side="left")

            term_lbl = ctk.CTkLabel(container, text=f"Raw SSH output: {output.splitlines()[0] if output else ''}", font=FONT_MONO_SMALL, text_color=TEXT_MUTED)
            term_lbl.pack(anchor="w", pady=(0, 10))

            btn_row = ctk.CTkFrame(container, fg_color="transparent")
            btn_row.pack(fill="x", side="bottom")

            ctk.CTkButton(
                btn_row,
                text="Close",
                fg_color=BTN_SECONDARY_BG,
                hover_color=BTN_SECONDARY_HOVER,
                text_color=BTN_SECONDARY_TEXT,
                border_width=1,
                border_color=BORDER_COLOR,
                command=self.destroy,
                width=100,
                height=36,
                font=FONT_BODY,
            ).pack(side="right")

    def _copy_key(self):
        if self.public_key_content:
            self.clipboard_clear()
            self.clipboard_append(self.public_key_content)
            self.update()
            if hasattr(self, "copy_key_btn"):
                self.copy_key_btn.configure(text="✓ Copied!", text_color=ACCENT_GREEN)

    def _copy_url(self):
        self.clipboard_clear()
        self.clipboard_append(self.ssh_settings_url)
        self.update()
        if hasattr(self, "copy_link_btn"):
            self.copy_link_btn.configure(text="✓ Copied!", text_color=ACCENT_GREEN)


class SSHActiveDeleteBlockDialog(BaseDialog):
    """Prompt shown when an SSH key is actively connected to GitHub and cannot be deleted."""
    def __init__(self, parent, key_name: str, username: Optional[str] = None):
        super().__init__(parent, "Cannot Delete Active SSH Key", 580, 420)
        self.ssh_settings_url = "https://github.com/settings/keys"

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=25)

        ctk.CTkLabel(
            container,
            text="⚠️  Cannot Delete Active SSH Key",
            font=FONT_HEADING,
            text_color=ACCENT_ORANGE,
        ).pack(anchor="w", pady=(0, 6))

        user_text = f"authenticated on GitHub as @{username}" if username else "connected and active on GitHub"
        ctk.CTkLabel(
            container,
            text=f"The SSH key '{key_name}' is currently {user_text}.\n\n"
                 "To prevent broken repository access or orphan keys, please delete or revoke the key from your GitHub account first.",
            font=FONT_BODY,
            text_color=TEXT_PRIMARY,
            justify="left",
            wraplength=520,
        ).pack(anchor="w", pady=(0, 16))

        # Instructions Box with Link
        card = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(0, 18))

        ctk.CTkLabel(card, text="GitHub SSH Keys Management URL:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(12, 4))

        link_row = ctk.CTkFrame(card, fg_color=BG_INSET, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
        link_row.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(link_row, text=self.ssh_settings_url, font=FONT_MONO, text_color=ACCENT_BLUE).pack(side="left", padx=12, pady=8)

        self.copy_btn = ctk.CTkButton(
            link_row,
            text="📋 Copy Link",
            width=95,
            height=28,
            font=FONT_SMALL,
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            command=self._copy_link,
        )
        self.copy_btn.pack(side="right", padx=8)

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        ctk.CTkButton(
            btn_row,
            text="Understood",
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            text_color="#ffffff",
            command=self.destroy,
            width=120,
            height=36,
            font=FONT_BODY_BOLD,
        ).pack(side="right")

    def _copy_link(self):
        self.clipboard_clear()
        self.clipboard_append(self.ssh_settings_url)
        self.update()
        self.copy_btn.configure(text="✓ Copied!", text_color=ACCENT_GREEN)


class ConfirmDeleteDialog(BaseDialog):
    """Confirmation modal for safe deletion."""
    def __init__(
        self,
        parent,
        title: str,
        heading: str,
        message: str,
        on_confirm: Callable[[], None],
    ):
        super().__init__(parent, title, 520, 300)
        self.on_confirm = on_confirm

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=25)

        ctk.CTkLabel(container, text=heading, font=FONT_HEADING, text_color=ACCENT_RED).pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(container, text=message, font=FONT_BODY, text_color=TEXT_PRIMARY, justify="left", wraplength=460).pack(anchor="w", pady=(0, 20))

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            fg_color=BTN_SECONDARY_BG,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=BTN_SECONDARY_TEXT,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self.destroy,
            width=100,
            height=36,
            font=FONT_BODY,
        )
        cancel_btn.pack(side="left")

        delete_btn = ctk.CTkButton(
            btn_row,
            text="Delete Permanently",
            fg_color=ACCENT_RED,
            hover_color=ACCENT_RED_HOVER,
            text_color="#ffffff",
            command=self._handle_delete,
            width=160,
            height=36,
            font=FONT_BODY_BOLD,
        )
        delete_btn.pack(side="right")

    def _handle_delete(self):
        self.on_confirm()
        self.destroy()