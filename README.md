# 🐙 GitHub Multi-Account Manager

A secure, modern Desktop GUI application built with **Python**, **uv**, and **CustomTkinter** for managing multiple GitHub accounts across different directories (e.g., \/personal\ and \/professional\ workflows).

---

## ✨ Features

- **📂 Automatic Directory-to-Account Mapping (includeIf)**:
  - Automatically configures Git conditional includes (\[includeIf "gitdir/i:<folder>/"]\).
  - Seamlessly switch between Personal, Work, or Freelance accounts based on your working folder (e.g. \D:/Personal/\ vs \D:/Professional/\).
  - Standard \git clone git@github.com:...\, commit, push, and pull commands work with the correct author and SSH key without manual switching or URL rewriting.

- **👤 Multi-Profile & Account Management**:
  - Store multiple profiles with individual Git author names, commit emails, and GitHub handles.
  - Automatically generates and synchronizes \~/.gitconfig-<profile>\ configuration files.

- **🔐 Secure Token Authentication (GitHub PAT)**:
  - Log in with GitHub Personal Access Tokens (PAT).
  - Tokens are encrypted and saved securely using the **Windows Credential Manager / OS Keyring** (\keyring\).
  - Auto-fetches profile details (Username, Avatar, Primary Verified Email, and Token Scopes).

- **🔑 Complete SSH Key Manager**:
  - Discover and view existing SSH keys in \~/.ssh/\.
  - Generate new high-security **ED25519** (or RSA 4096-bit) SSH key pairs with one click.
  - Copy public keys to your clipboard instantly.
  - **1-Click Upload to GitHub**: Direct API upload of generated SSH keys to your GitHub account (no need to open a browser).
  - **Live SSH Connection Testing**: Test authentication with GitHub (\ssh -T\) directly inside the UI.

- **🔍 Live Git Inspector & Diagnostics**:
  - Browse or paste any folder path to verify which Git author identity and SSH key will be used.
  - Live test SSH connectivity using the folder's assigned credentials.

- **⚙️ Safety & Backups**:
  - Automated timestamped backups of \~/.gitconfig\ before making changes.
  - Built-in backup restoration and live config preview.
  - Modern Dark / Light theme support.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Git for Windows / OpenSSH

### Installation & Run

1. **Clone or navigate to the project directory:**
   `ash
   cd D:\Personal\Projects\github-multi-account-manager
   `

2. **Run the Application with \uv\:**
   `ash
   uv run github-account-manager
   `
   *Alternatively, run with Python:*
   `ash
   uv run python main.py
   `

3. **Run Unit Tests:**
   `ash
   uv run pytest
   `

---

## 📁 Project Architecture

\\\
github-multi-account-manager/
├── pyproject.toml               # uv project definitions and dependencies
├── README.md                    # Project documentation
├── main.py                      # Development launcher
├── src/
│   └── github_account_manager/
│       ├── config.py            # App constants, paths, and settings
│       ├── models.py            # Pydantic data schemas (Account, FolderMapping, SSHKeyInfo)
│       ├── services/
│       │   ├── git_service.py   # Git config parser, writer, includeIf manager & backups
│       │   ├── ssh_service.py   # SSH key generator, discovery, and live connection tester
│       │   ├── github_service.py# GitHub REST API client (PAT auth & key upload)
│       │   ├── keyring_service.py # OS Keyring / Windows Credential Manager integration
│       │   └── manager.py       # Core orchestrator coordinating state & synchronization
│       └── ui/
│           ├── app.py           # Main CustomTkinter desktop window
│           ├── theme.py         # Color palette, styling, and typography
│           ├── components/      # UI components (Cards, Badges, Modals, Pickers)
│           └── views/           # Accounts, Folders, SSH, Inspector, and Settings views
└── tests/                       # Complete pytest test suite
\\\

---

## 🛡️ Security Note
All sensitive tokens (PATs) are kept strictly in the OS-level credential vault (Windows Credential Manager) and are never stored in plain text files.