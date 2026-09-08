# 📋 SSH Workflow Improvements & Bidirectional Account-Key Linking Plan

## 🎯 Objectives
1. **Eliminate Clipboard Collision in SSH Setup Modal**:
   - In `SSHTestGuideDialog` (modal prompted when SSH connection is untested or rejected by GitHub), replace the `📋 Copy Link` button with an **`↗ Go to Link`** (or `🌐 Open in Browser`) button.
   - Clicking this button opens `https://github.com/settings/keys` directly in the user's default browser via `webbrowser.open()`.
   - This prevents the URL from overwriting the public SSH key in the user's clipboard, eliminating the need to copy the SSH key twice.
   - Also update `SSHActiveDeleteBlockDialog` to provide direct browser launch.

2. **Bidirectional Account & SSH Key Configuration**:
   - Currently, accounts have a dropdown on the **Accounts Page** to select an SSH key (`AddEditAccountDialog`), but the **SSH Page** has no way to view or assign which account profile is linked to a key.
   - Add an **Account Profile Dropdown** to each SSH key card on the **SSH Page** (`SSHView`), allowing users to link or reassign SSH keys directly without navigating back and forth.
   - Add an optional **"Link to Account"** selector inside `NewSSHKeyDialog` so newly generated SSH keys can be bound to a profile immediately upon creation.

---

## 🏗️ Architecture & Component Breakdown

```
┌─────────────────────────────────────────────────────────┐
│                     AccountManager                      │
│  - link_ssh_key_to_account(ssh_key_path, account_id)    │
│  - get_account_for_ssh_key(ssh_key_path)                │
│  - auto-syncs settings & git configuration              │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
               ▼                          ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐
│           SSHView           │  │     NewSSHKeyDialog         │
│  - Card Account Dropdown    │  │  - "Link to Account" combo  │
│  - Linked Profile Badge     │  │  - Auto-fill email & name   │
│  - Instant sync on change   │  │  - Instant link on create   │
└─────────────────────────────┘  └─────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│                   SSHTestGuideDialog                    │
│  - Step 1: "📋 Copy Key" (copies public SSH key)       │
│  - Step 2: "↗ Go to Link" (opens browser without        │
│             overwriting clipboard)                      │
└─────────────────────────────────────────────────────────┘
```

---

## 📌 Phased Implementation Tasks

### Phase 1: SSH Test & Guide Modal UX Fix (`ui/components/dialogs.py`)
- [x] **1.1 Update `SSHTestGuideDialog` Step 2**:
  - Replace `self.copy_link_btn` (`📋 Copy Link`) with `self.open_link_btn` (`↗ Go to Link` / `🌐 Open in Browser`).
  - Wire command to `self._open_url()`, executing `webbrowser.open(self.ssh_settings_url)` in a non-blocking daemon thread.
  - Update button feedback on click (temporary text `"✓ Opened!"`).
  - Preserve public SSH key in clipboard untouched.
- [x] **1.2 Update `SSHActiveDeleteBlockDialog`**:
  - Add an `"↗ Go to Link"` button alongside `"📋 Copy Link"` so users can immediately navigate to GitHub to delete/revoke active keys.

---

### Phase 2: Service Layer Support for Bidirectional Linking (`services/manager.py`)
- [x] **2.1 Add `get_account_for_ssh_key(ssh_key_path: str) -> Optional[Account]`**:
  - Return the account configured with this key (matching full path or basename `Path(p).name.lower()`).
- [x] **2.2 Add `link_ssh_key_to_account(ssh_key_path: str, account_id: Optional[str]) -> Tuple[bool, str]`**:
  - If `account_id` is `None`: unlink this key from any account currently using it.
  - If `account_id` is provided:
    - Unlink this key from previous accounts to prevent conflicting assignments.
    - Set target account's `ssh_key_path = ssh_key_path`.
  - Trigger `self.save_settings()` which automatically calls `self.sync_git()`.
  - Return status and descriptive message for notification toasts.

---

### Phase 3: SSH Page Account Selector (`ui/views/ssh_view.py`)
- [x] **3.1 Display Linked Profile in Key Card Header**:
  - If a key is linked to an account, show a badge: `👤 {account.name}` (`StatusBadge(..., "success")`).
  - If unlinked, display an `Unlinked` (`StatusBadge(..., "muted")`) badge.
- [x] **3.2 Add Account Dropdown Row to Key Card**:
  - Add a dedicated row: `"Linked Account Profile:"` with `CTkComboBox`.
  - Populate with options: `["None (Unassigned)"] + [f"{acc.name} ({acc.email})" for acc in accounts]`.
  - Pre-select the currently linked account.
  - On change: call `self.manager.link_ssh_key_to_account(...)`, notify user, and update card UI / badges without full page flicker.
- [x] **3.3 Update `NewSSHKeyDialog` Integration**:
  - Pass `self.manager.settings.accounts` to `NewSSHKeyDialog`.
  - Add optional `"Link to Account Profile"` dropdown in `NewSSHKeyDialog`.
  - If an account is selected:
    - Pre-fill email and suggest filename `id_ed25519_{acc.name.lower()}`.
    - Upon successful generation, automatically link the new key to the account.

---

### Phase 4: Unit Testing & Verification
- [x] **4.1 Test Service Layer Linking**:
  - Add unit tests in `tests/test_manager.py` verifying:
    - Linking an SSH key to an account updates `account.ssh_key_path`.
    - Switching key to another account unlinks the previous one.
    - Setting to `None` unlinks the key.
    - `get_account_for_ssh_key` accurately identifies linked accounts by path and filename.
- [x] **4.2 Test Dialog Behavior**:
  - Unit test verifying `SSHTestGuideDialog` and `NewSSHKeyDialog` APIs in `tests/test_ssh_workflow_ui.py`.
- [x] **4.3 Full Test Suite & Build Check**:
  - Run `uv run pytest` across all 44 tests (100% passing).
  - Rebuild executable via `uv run python build.py --publish-dir "D:\Professional\Publish"`.
  - Update Graphify map.
