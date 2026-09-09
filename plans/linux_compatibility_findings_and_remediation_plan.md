# 📋 Linux Compatibility & Native Reliability Plan

## 🎯 Objective
Achieve full, out-of-the-box compatibility and native execution on **Linux** (Linux Mint, Ubuntu, Debian, Fedora, Arch) for the GitHub Multi-Account Manager application. This plan addresses the root causes behind silent startup crashes, missing GUI dependencies, insecure credential parsing, platform-specific service assumptions, and release binary dynamic library bundling failures.

---

## 🏗️ Architecture & Component Context

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Application Launchers                         │
│  - main.py (Entry script & PyInstaller entry)                          │
│  - src/github_account_manager/main.py (Package entry point)            │
│  * Pre-flight Tkinter probe, TTY stderr preservation, explicit exits   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                             Core Services                              │
│  ┌───────────────────────────────┐   ┌───────────────────────────────┐ │
│  │     LinuxPlatformAdapter      │   │        KeyringService         │ │
│  │  - ~/.config & XDG scanning   │   │  - Freedesktop SecretService  │ │
│  │  - URL parsing without leak   │   │  - Cross-platform encrypted   │ │
│  │  - Target-specific deletion   │   │    vault fallback (no DPAPI)  │ │
│  └───────────────────────────────┘   └───────────────────────────────┘ │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        GUI & Standalone Release                        │
│  - ui/app.py: Wayland topmost safety, Linux iconphoto() PNG icon       │
│  - github-account-manager.spec: Bundled Tcl/Tk 8.6 shared libs & data  │
│  - .github/workflows/release.yml: Ubuntu LTS compatible build baseline │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Linux Audit Findings & Root Causes

### 1. Missing System Tkinter Dependency (`python3-tk`) in Dev Environments
* **Severity**: 🔴 Critical (App Blocker for source/dev execution)
* **Location**: `src/github_account_manager/main.py:11`, `src/github_account_manager/ui/app.py:4`, `tests/test_ssh_workflow_ui.py:2`
* **Root Cause**: `customtkinter` depends on Python's native `tkinter` module. Debian/Ubuntu/Mint distributions exclude `tkinter` from standard `python3` packages. Virtual environments (`.venv`) created from system Python inherit this absence.
* **Error Log**: `ModuleNotFoundError: No module named 'tkinter'`

### 2. Silent Startup Crash & Console Error Swallowing
* **Severity**: 🔴 High (Diagnostic Blocker)
* **Location**: `main.py:54-74`, `src/github_account_manager/main.py:51-72`
* **Root Cause**: All stdout and stderr streams are redirected to `LogStream` writing to `debug.log`. When `tkinter` is missing, `global_excepthook` attempts to display a GUI error dialog using `tkinter`, which fails silently (`except Exception: pass`) and terminates with exit code `0`. To a terminal user, the command exits instantly with zero feedback.

### 3. Windows-Specific Token Fallback (`DPAPIFallback`)
* **Severity**: 🟠 High (Data Loss / Persistence Failure)
* **Location**: `src/github_account_manager/services/keyring_service.py:24-65`
* **Root Cause**: When the OS keyring backend fails (e.g. headless session, locked Secret Service, SSH), `KeyringService` calls `DPAPIFallback` which executes `ctypes.windll.crypt32.CryptProtectData`. On Linux, `ctypes.windll` does not exist, raising `AttributeError: module 'ctypes' has no attribute 'windll'` and preventing token storage.

### 4. Secret Credential Leaking in Linux Scanner
* **Severity**: 🟠 High (Security / Information Disclosure)
* **Location**: `src/github_account_manager/platform/linux.py:267-272`
* **Root Cause**: `~/.git-credentials` entries formatted as `https://username:token@github.com` are parsed using `line.split("@")[0].split("//")[-1]`. This extracts `username:token`, exposing personal access tokens in the UI credentials list.

### 5. Release Binary Crash: Missing `libtcl9tk9.0.so` in Linux Release (`v0.1.29`)
* **Severity**: 🔴 Critical (Release File Blocker)
* **Location**: `github-account-manager-linux-x64.tar.gz` (`main.py:89` ➔ `tkinter/__init__.py:38`)
* **Root Cause**: Tested against the official `v0.1.29` GitHub release binary. The binary crashes immediately with:
  ```text
  ImportError: libtcl9tk9.0.so: cannot open shared object file: No such file or directory
  ```
  On GitHub Actions (`ubuntu-latest`), Python built against Tcl/Tk 9.0 (`libtcl9tk9.0.so`). However, target end-user Linux distributions (Ubuntu 24.04/22.04, Linux Mint, Debian) supply Tcl/Tk 8.6 (`libtcl8.6.so`). PyInstaller dynamically links against the builder's host Tcl/Tk shared library instead of bundling compatible runtime libraries.

---

## 📌 Phased Implementation Tasks

### Phase 1: Startup Diagnostics, Pre-Flight Probes & Console UX
- [x] **1.1 Preserve Terminal Error Streams (`main.py` & `src/github_account_manager/main.py`)**:
  - Keep references to `sys.__stderr__` and `sys.__stdout__`.
  - When running in a console/terminal environment (`sys.stdin.isatty()` or not frozen), write uncaught errors to `sys.__stderr__` in addition to `debug.log`.
  - Ensure any startup exception results in an explicit non-zero exit code (`sys.exit(1)`).
- [x] **1.2 Pre-Flight Tkinter Probe & Actionable Error Message (`main.py`)**:
  - Perform a lightweight probe for `tkinter` before executing GUI imports.
  - If `tkinter` is missing, print a formatted, actionable warning directly to the terminal:
    ```text
    ======================================================================
    [ERROR] Python Tkinter is not installed on this system!
    ----------------------------------------------------------------------
    The application GUI requires Tkinter. Install it with:
      • Ubuntu / Debian / Linux Mint:  sudo apt install python3-tk
      • Fedora / RHEL:                 sudo dnf install python3-tkinter
      • Arch Linux:                    sudo pacman -S tk
    ======================================================================
    ```
- [x] **1.3 Hardened Exception Hook (`main.py:58-74`)**:
  - In `global_excepthook()`, wrap the `import tkinter as tk` fallback in safe error handling.
  - If `tkinter` cannot be imported, fall back to printing the error report to terminal `sys.__stderr__`.
- [x] **1.4 Linux Prerequisites Documentation (`README.md`)**:
  - Add a dedicated Linux Installation section in `README.md` specifying `sudo apt install python3-tk` alongside `uv` setup instructions.

---

### Phase 2: Cross-Platform Keyring Fallback Vault (`services/keyring_service.py`)
- [x] **2.1 Isolate Windows DPAPI to Windows-Only Execution**:
  - Wrap `class DPAPIFallback` and `from ctypes import wintypes` under `if sys.platform == "win32"` conditional logic.
  - Prevent `AttributeError: module 'ctypes' has no attribute 'windll'` on Linux and macOS.
- [x] **2.2 Implement Cross-Platform Vault Fallback (`LinuxVaultFallback`)**:
  - When `keyring.set_password()` or `keyring.get_password()` fails on Linux (e.g. headless environment, locked Secret Service, or missing daemon), use a secure local vault.
  - Derive a machine/user-bound key using SHA-256 / PBKDF2 over machine-id (`/etc/machine-id` or hostname + username).
  - Encrypt fallback entries in `~/.github_account_manager/.vault.dat` using AES / Fernet (supported via `cryptography` package already in lockfile).
  - Enforce strict POSIX file permissions: `os.chmod(vault_file, 0o600)` and directory permissions `0o700`.
- [x] **2.3 Fallback Unit Tests (`tests/test_security.py`)**:
  - Add unit test `test_cross_platform_vault_fallback()` validating token storage, retrieval, and deletion when the system keyring backend is simulated as unavailable.

---

### Phase 3: Linux Credential Scanner & Security Hardening (`platform/linux.py`)
- [x] **3.1 Sanitize Stored Git Credential Parser (`linux.py:259-275`)**:
  - Replace naive `line.split("@")[0].split("//")[-1]` with `urllib.parse.urlsplit`.
  - Extract only `parsed.username` (e.g. `john`), masking or omitting `parsed.password` to prevent leaking Personal Access Tokens into the UI credential list.
- [x] **3.2 Target-Aware Credential Deletion (`linux.py:297-320`)**:
  - In `delete_git_credential(target)`:
    - If `target` refers to `~/.git-credentials`, only remove lines matching that specific target URL/user.
    - If `target` refers to `libsecret`, run `secret-tool clear` targeting only the specific host/service rather than a blanket wipe.
- [x] **3.3 Safe XDG Path Resolution (`linux.py:20-70`)**:
  - Use `os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")` to guard against empty strings (`XDG_CONFIG_HOME=""`).

---

### Phase 4: Linux Desktop Integration & Wayland Resilience (`ui/app.py`)
- [ ] **4.1 Linux Window Icon Support (`ui/app.py:52-59`)**:
  - On Linux and macOS, load `assets/navbar-logo-dark.png` or `assets/icon.png` using `ImageTk.PhotoImage` and call `self.iconphoto(True, img)` so the window displays a native application icon instead of the default Tk logo.
- [ ] **4.2 Wayland & Tiling Window Manager Protection (`ui/app.py:69-74`)**:
  - Wrap `self.attributes("-topmost", True)` and `self.lift()` in `try...except Exception` blocks to prevent crashes on Wayland compositors or tiling window managers (i3, sway, Hyprland).
- [ ] **4.3 Linux Font Stack Fallback (`platform/linux.py` & `ui/theme.py`)**:
  - In `LinuxPlatformAdapter.get_system_font_family()`, check for installed fonts: `Ubuntu`, `Inter`, `Cantarell`, `DejaVu Sans`, returning the best match or `"sans-serif"`.

---

### Phase 5: Standalone Packaging, Tcl/Tk Bundling & CI/CD Pipeline (Fix 1)
- [ ] **5.1 Bundle Tcl/Tk Shared Libraries & Data in PyInstaller (`github-account-manager.spec`)**:
  - In `github-account-manager.spec`, on Linux:
    - Automatically discover and collect `libtcl8.6.so*`, `libtk8.6.so*`, and `libBLT*.so*` into `binaries`.
    - Collect Tcl and Tk asset directories (`/usr/share/tcltk/tcl8.6`, `/usr/share/tcltk/tk8.6`) into `datas`.
    - Include a custom runtime hook (`pyi_rth_tcltk_linux.py`) that exports `TCL_LIBRARY` and `TK_LIBRARY` pointing to `sys._MEIPASS` when running frozen, eliminating host OS library dependencies.
- [ ] **5.2 Fix GitHub Actions Linux Build Environment (`.github/workflows/release.yml`)**:
  - In `.github/workflows/release.yml`, on the `ubuntu-latest` (Linux) matrix runner:
    - Avoid using `uv python install 3.12` on Linux, which links against non-standard Tcl/Tk 9.0 (`libtcl9tk9.0.so`).
    - Build against the Ubuntu system Python (`/usr/bin/python3`) with `python3-tk`, `libtk8.6`, and `libtcl8.6` preinstalled, guaranteeing compatibility with all Debian/Ubuntu/Mint distributions.
    - Set runner base or container target to ensure lowest common denominator `glibc` (e.g. Ubuntu 22.04 LTS runner).
- [ ] **5.3 Direct Standalone Publishing on Linux (`build.py:175-190`)**:
  - In `publish_artifacts()`, add handling for `target_os == "linux"`:
    - Copy `dist/github-account-manager` directly to `publish/github-account-manager`.
    - Ensure executable file mode: `os.chmod(dest_bin, 0o755)`.
- [ ] **5.4 Automated Smoke Test for Release Binary in CI/CD**:
  - Add a verification step in `.github/workflows/release.yml` after Linux packaging:
    ```bash
    tar -xzf dist/github-account-manager-linux-x64.tar.gz -C /tmp/
    xvfb-run /tmp/github-account-manager --version
    ```
    Ensures missing `.so` libraries fail the pipeline before publishing the release.
- [ ] **5.5 Test Suite Verification on Linux**:
  - Run full test suite with `uv run pytest` once `python3-tk` is installed and verify 100% test pass rate.

---

## 🧪 Verification & Acceptance Criteria

| Check | Success Criteria |
| :--- | :--- |
| **Startup Diagnostics** | Running `.venv/bin/python main.py` without `python3-tk` prints a clear, human-readable terminal error with package manager instructions and exits with code 1. |
| **GUI Launch** | Running `.venv/bin/python main.py` with `python3-tk` launches the CustomTkinter GUI cleanly on Linux Mint / Ubuntu / Debian. |
| **Token Storage** | Adding an account stores the token in Secret Service or fallback vault with `0600` permissions. No `windll` errors. |
| **Git Credential Scanner** | Credential Inspector displays usernames only; tokens from `~/.git-credentials` are never visible. |
| **Release File (Fix 1)** | Downloaded `github-account-manager-linux-x64.tar.gz` runs immediately on a stock Linux install without `libtcl9tk9.0.so` errors. |
| **Full Test Suite** | `uv run pytest` passes all unit tests, including UI dialog tests (`test_ssh_workflow_ui.py`). |
| **Linux Packaging** | `python build.py` produces both `publish/github-account-manager` (executable) and `publish/github-account-manager-linux-x64.tar.gz`. |
