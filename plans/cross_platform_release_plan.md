# 📋 Cross-Platform Builds & Automated GitHub Release Plan

## 🎯 Objective
Transform the GitHub Multi-Account Manager application into a fully modular cross-platform solution supporting **Windows**, **macOS**, and **Linux**, with dedicated OS-separated source adapters and an automated **GitHub Actions Release CI/CD workflow** that publishes direct download links for all 3 OS versions on push to main.

---

## 🏗️ Modular Architecture & OS-Specific Separation

Standard cross-platform Python architecture with dedicated OS adapters in src/github_account_manager/platform/:

`
src/github_account_manager/platform/
├── __init__.py         # Platform factory: get_platform_adapter() based on sys.platform
├── base.py             # Abstract PlatformAdapter interface
├── windows.py          # Windows-specific: cmdkey, AppData paths, ProgramFiles
├── macos.py            # macOS-specific: security Keychain, ~/Library/Application Support, /Applications
└── linux.py            # Linux-specific: secret-tool, ~/.config, /usr/bin, desktop entries
`

### OS Comparison Matrix

| Feature / Service | Windows 🪟 (windows.py) | macOS 🍎 (macos.py) | Linux 🐧 (linux.py) |
| :--- | :--- | :--- | :--- |
| **Default SSH Directory** | %USERPROFILE%\.ssh | ~/.ssh | ~/.ssh |
| **Global Git Config** | %USERPROFILE%\.gitconfig | ~/.gitconfig | ~/.gitconfig |
| **VS Code Settings Path** | %APPDATA%\Code\User\settings.json | ~/Library/Application Support/Code/User/settings.json | ~/.config/Code/User/settings.json |
| **Cursor AI Settings Path** | %APPDATA%\Cursor\User\settings.json | ~/Library/Application Support/Cursor/User/settings.json | ~/.config/Cursor/User/settings.json |
| **Windsurf Settings Path** | %APPDATA%\Windsurf\User\settings.json | ~/Library/Application Support/Windsurf/User/settings.json | ~/.config/Windsurf/User/settings.json |
| **VSCodium Settings Path** | %APPDATA%\VSCodium\User\settings.json | ~/Library/Application Support/VSCodium/User/settings.json | ~/.config/VSCodium/User/settings.json |
| **Credential Manager** | cmdkey /list & cmdkey /delete | security find-internet-password / security delete-internet-password | secret-tool / Git credential helper |
| **Release Artifact** | github-account-manager-windows-x64.zip | github-account-manager-macos-universal.zip | github-account-manager-linux-x64.tar.gz |
| **Download Links** | Direct GitHub Release URL | Direct GitHub Release URL | Direct GitHub Release URL |

---

## 📌 Phased Implementation Checklist

### Phase 1: Cross-Platform Modular Architecture & OS Adapters
- [x] **1.1 Abstract Platform Interface (`platform/base.py`)**:
  - Define `PlatformAdapter` interface for IDE paths, credential inspection, app scanning, and system font discovery.
- [x] **1.2 Dedicated Windows Adapter (`platform/windows.py`)**:
  - Implement Windows Registry, `cmdkey`, `%APPDATA%`, and `%LOCALAPPDATA%` paths.
- [x] **1.3 Dedicated macOS Adapter (`platform/macos.py`)**:
  - Implement macOS `/Applications`, `~/Library/Application Support`, and `security` Keychain integration.
- [x] **1.4 Dedicated Linux Adapter (`platform/linux.py`)**:
  - Implement Linux `~/.config`, `~/.local/share/applications`, `/usr/bin`, and `secret-tool` integration.
- [x] **1.5 Platform Factory & Service Integration (`platform/__init__.py`)**:
  - Wire `AppIntegrationService`, `GitService`, and `config.py` to use `get_platform_adapter()`.
- [x] **1.6 Cross-Platform Font Fallbacks (`ui/theme.py`)**:
  - Fallback font stacks: `Segoe UI` (Windows), `SF Pro Text` / `Helvetica Neue` (macOS), `Ubuntu` / `DejaVu Sans` (Linux).
- [x] **1.7 Unit Tests for All OS Adapters**:
  - Write test suite in `tests/test_platform_adapters.py` testing Windows, macOS, and Linux adapters.

---

### Phase 2: PyInstaller Packaging & Build Automation
- [x] **2.1 Universal Build Spec (`build.py`)**:
  - Created PyInstaller build script that bundles CustomTkinter assets, fonts, and theme files.
- [x] **2.2 Platform Asset Bundling & Compression**:
  - Automated `.zip` archive for Windows & macOS, `.tar.gz` for Linux.
- [x] **2.3 Dependency Configuration**:
  - Added `pyinstaller` to dev dependencies in `pyproject.toml`.

---

### Phase 3: GitHub Actions CI/CD Release Pipeline
- [x] **3.1 Multi-OS Build Matrix**:
  - Created `.github/workflows/release.yml` with matrix strategy running on `windows-latest`, `macos-latest`, and `ubuntu-latest`.
- [x] **3.2 Automated Test Gate**:
  - Runs `uv run pytest` (with `xvfb` for headless Linux testing) before packaging.
- [x] **3.3 Automated Packaging & Compression**:
  - Generates `github-account-manager-windows-x64.zip`, `github-account-manager-macos.zip`, and `github-account-manager-linux-x64.tar.gz`.
- [x] **3.4 Automated GitHub Release with Download Links**:
  - Configured `softprops/action-gh-release@v2` with markdown release notes containing direct download links for all 3 OS versions.

---

### Phase 4: Verification, Testing & Documentation
- [x] **4.1 Full Test Suite Execution**:
  - 24 unit tests passing cleanly across services and platform adapters (`uv run pytest`).
- [x] **4.2 Update README.md with Direct Download Links**:
  - Added OS download table with release links and modular platform architecture diagram.
