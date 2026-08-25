# 🐙 GitHub Multi-Account Manager

A secure, modern desktop GUI application built with **Python 3.12+**, **uv**, and **CustomTkinter** for seamless management of multiple GitHub accounts across different directories (e.g., Personal, Work, Freelance, or Client projects) on Windows.

Eliminates cross-account permission collisions, IDE account hijacking (VS Code, Cursor), and corporate firewall blocks without requiring any personal access tokens.

---

## 🌟 Key Highlights

* **📂 Automatic Directory Routing (includeIf)**: Repositories in D:/Personal automatically commit as your personal account; repositories in D:/Professional automatically commit as your work account.
* **🛡️ External IDE & App Isolation**: Prevents VS Code and Cursor from injecting their logged-in GitHub account into your Git repositories with 1-click isolation (github.gitAuthentication: false).
* **🔑 Tokenless SSH Key Architecture**: Works 100% via dedicated ED25519 SSH keys. No Personal Access Tokens (PATs) or token expiration to worry about.
* **⚡ SSH Port 443 & Firewall Bypass**: Automatically routes SSH connections through ssh.github.com:443 with IdentitiesOnly yes, bypassing corporate firewall port 22 blocks and strict identity collisions.
* **🔄 HTTPS ➔ SSH Protocol Converter**: 1-click scanner and converter that maps repositories to their dedicated profile SSH keys.
* **🧹 Windows Credential Vault Manager**: Inspects and clears cached global tokens (git:https://github.com) from Windows Credential Manager.
* **⚡ Non-Blocking Async UI**: Powered by a background task runner with real-time button loaders (⏳ Testing..., ⏳ Scanning..., ⏳ Converting...) and rich error modal windows.
* **💡 In-App Contextual Guidance**: Every section features built-in explainers detailing **What it does**, **Why it's needed**, and **How it works**.

---

## ✨ Feature Breakdown

### 1. 👤 Account Profiles & Git Identities
- Store multiple independent profiles with custom **Git Author Names**, **Commit Emails**, and **GitHub Handles**.
- Auto-fill profile info from GitHub using an Email or Username (@octocat).
- Generates isolated ~/.gitconfig-<profile> configuration files with atomic file replacement.

### 2. 📁 Workspace Directory Mappings
- Map entire folders (e.g. D:/Personal/Projects or D:/Professional/Projects) to specific profiles.
- Native Git [includeIf "gitdir/i:<path>"] integration ensures Git CLI, IDEs, and GUI tools apply the right identity without running manual git config commands.

### 3. 🔑 Complete SSH Key Lifecycle Manager
- **Discovery**: Automatically discovers all RSA and ED25519 keys in ~/.ssh/.
- **Generation**: Generate new high-security **ED25519** (or RSA 4096-bit) key pairs with optional passphrases in one click.
- **Live Connection Testing**: Test live SSH authentication against GitHub (ssh -T) with interactive in-app setup guides.
- **Safe Deletion Guard**: Tests keys before deletion—if a key is still active on GitHub, deletion is blocked with a direct revocation link.

### 4. 🧩 External Apps & IDE Isolation (Apps & Integrations)
- **Universal App Scanner**: Discovers installed code editors (VS Code, Cursor AI, Windsurf, VSCodium) and Git GUI clients (GitHub Desktop, Visual Studio).
- **1-Click Folder Isolation**: Configures code editors to respect local folder Git configs and stop hijacking commits with their active editor login.
- **Windows Credential Manager Cleanup**: Detects and deletes conflicting global Git credentials cached in Windows Vault.
- **Repository Remote Converter**: Converts repositories between HTTPS and dedicated SSH aliases with 1-click bulk support.

### 5. 🔍 Live Git & Directory Inspector
- Inspect any folder or repository path to simulate and view the exact Git identity (user.name, user.email) and core.sshCommand Git will use.
- Live-test SSH connectivity for mapped directory profiles.

### 6. ⚙️ Automatic Backups & Safety
- Automated timestamped backups of ~/.gitconfig stored in ~/.github_account_manager/backups/.
- 1-click backup restoration and live ~/.gitconfig preview.
- Dark, Light, and System theme support with full high-contrast readability.

---

## 🚀 Getting Started

### Prerequisites
- **Windows 10 / 11**
- **Python 3.12+**
- [**uv**](https://docs.astral.sh/uv/) (recommended) or pip
- **Git for Windows** & **OpenSSH**

### Quickstart

1. **Clone the repository:**
   `powershell
   git clone https://github.com/Optirius/github-multi-account-manager.git
   cd github-multi-account-manager
   `

2. **Run with uv:**
   `powershell
   uv run github-account-manager
   `

   *Or run directly with Python:*
   `powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e .
   python -m github_account_manager
   `

3. **Run Unit Tests:**
   `powershell
   uv run pytest
   `

---

## 🏗️ Architecture & Project Structure

`
github-multi-account-manager/
├── pyproject.toml               # uv project configuration and dependencies
├── README.md                    # Project documentation
├── main.py                      # Development entry point
├── src/
│   └── github_account_manager/
│       ├── config.py            # App paths, directories, and constants
│       ├── models.py            # Pydantic schemas (Account, FolderMapping, SSHKeyInfo)
│       ├── services/
│       │   ├── git_service.py   # Git config includes, profiles, ~/.ssh/config & backups
│       │   ├── ssh_service.py   # SSH key generation, discovery & live testing
│       │   ├── github_service.py# GitHub REST API public search & discovery
│       │   ├── app_integration_service.py # IDE isolation, cmdkey & repo scanner
│       │   └── manager.py       # Core orchestrator coordinating state & sync
│       └── ui/
│           ├── app.py           # Main CustomTkinter application window & navigation
│           ├── async_runner.py  # Non-blocking async background executor with loaders
│           ├── theme.py         # Color palettes, typography & high-contrast themes
│           ├── components/      # Cards, Badges, Modals, InfoBanners, Dialogs
│           │   ├── account_card.py
│           │   ├── folder_row.py
│           │   ├── info_banner.py
│           │   ├── status_badge.py
│           │   └── dialogs.py   # SSH guides, Deletion guard & Error modals
│           └── views/           # Accounts, Folders, SSH, Apps, Inspector & Settings
└── tests/                       # Complete pytest test suite (19 unit tests)
`

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).