# Repository Instructions & Operational Rules

## 1. Single Source of Truth Version Management Protocol
- The primary source of truth for the application version is `version.txt` located in the repository root.
- `src/github_account_manager/version.py` reads directly from `version.txt` and synchronizes canonical `__version__`.
- Both `build.py` and GitHub Actions (`release.yml`) read the release version directly from `version.txt` / `version.py`.

## 2. Commit & Pre-Release Version Check Rule
- **Mandatory Pre-Commit Evaluation**:
  Before committing changes or completing feature tasks, evaluate whether `version.txt` requires a version bump:
  - **Patch Bump** (e.g. `0.2.0` ➔ `0.2.1`): For bug fixes, UI styling adjustments, test updates, or platform compatibility patches.
  - **Minor Bump** (e.g. `0.2.0` ➔ `0.3.0`): For new features, newly supported IDEs, dialogs, or workflow additions.
  - **Major Bump** (e.g. `0.2.0` ➔ `1.0.0`): For breaking architectural shifts or general availability milestones.
- **Consistency Enforcement**:
  - When bumping the version, update `version.txt` (or call `set_version()` which updates both `version.txt` and `src/github_account_manager/version.py`).
  - Never commit mismatched versions between `version.txt` and `src/github_account_manager/version.py`.

## 3. Graphify Code Map Protocol
- Before performing codebase refactoring or analyzing component dependencies:
  1. Check if a Graphify map exists at `D:/Professional/graphify/projects/github-multi-account-manager/graphify-out/graph.json`.
  2. If code changes occurred, refresh the map:
     `graphify . --out "D:/Professional/graphify/projects/github-multi-account-manager" --code-only`
