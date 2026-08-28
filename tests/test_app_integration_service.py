import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from github_account_manager.models import FolderMapping
from github_account_manager.services.app_integration_service import AppIntegrationService


def test_parse_owner_repo():
    service = AppIntegrationService()
    assert service._parse_owner_repo("https://github.com/user-org/my-repo.git") == "user-org/my-repo"
    assert service._parse_owner_repo("https://github.com/user-org/my-repo") == "user-org/my-repo"
    assert service._parse_owner_repo("git@github.com:company-org/work-repo.git") == "company-org/work-repo"
    assert service._parse_owner_repo("ssh://git@github.com/org/proj.git") == "org/proj"
    assert service._parse_owner_repo("") == ""


def test_vscode_isolation_workflow(tmp_path):
    settings_file = tmp_path / "Code" / "User" / "settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(json.dumps({"editor.fontSize": 14}), encoding="utf-8")

    from github_account_manager.platform.windows import WindowsPlatformAdapter

    class MockPlatform(WindowsPlatformAdapter):
        def get_ide_settings_paths(self, ide_id: str):
            if ide_id == "vscode":
                return [settings_file]
            return []

    service = AppIntegrationService(platform=MockPlatform())

    apps = service.detect_all_installed_apps()
    vscode_app = next((a for a in apps if a["id"] == "vscode"), None)
    assert vscode_app is not None
    assert vscode_app["installed"] is True
    assert vscode_app["is_isolated"] is False

    # Apply isolation
    success, msg = service.apply_isolation_to_app("vscode")
    assert success is True

    # Check updated settings
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert data["github.gitAuthentication"] is False
    assert data["git.terminalAuthentication"] is False

    apps_updated = service.detect_all_installed_apps()
    vscode_app_updated = next(a for a in apps_updated if a["id"] == "vscode")
    assert vscode_app_updated["is_isolated"] is True

    # Restore defaults
    success, msg = service.restore_defaults_for_app("vscode")
    assert success is True
    data_restored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert "github.gitAuthentication" not in data_restored


def test_convert_repo_remote(tmp_path):
    repo_dir = tmp_path / "my_project"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    service = AppIntegrationService()

    with patch.object(service, "_get_repo_remote_url", return_value="https://github.com/test-org/my-portfolio.git"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        success, msg = service.convert_repo_remote(repo_dir, "ssh")
        assert success is True
        assert "git@github.com:test-org/my-portfolio.git" in msg


def test_delete_windows_credential_alias():
    service = AppIntegrationService()
    with patch.object(service, "delete_windows_git_credential", return_value=(True, "Deleted")):
        success, msg = service.delete_windows_credential("git:https://github.com")
        assert success is True
        assert msg == "Deleted"


def test_enable_git_credential_use_http_path():
    service = AppIntegrationService()
    with patch("github_account_manager.services.app_integration_service.safe_subprocess_run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        success, msg = service.enable_git_credential_use_http_path()
        assert success is True
        assert "credential.useHttpPath" in msg