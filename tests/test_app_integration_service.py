import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from github_account_manager.models import FolderMapping
from github_account_manager.services.app_integration_service import AppIntegrationService


def test_parse_owner_repo():
    service = AppIntegrationService()
    assert service._parse_owner_repo("https://github.com/Optirius/my-repo.git") == "Optirius/my-repo"
    assert service._parse_owner_repo("https://github.com/Optirius/my-repo") == "Optirius/my-repo"
    assert service._parse_owner_repo("git@github.com:tahmid-selise/work-repo.git") == "tahmid-selise/work-repo"
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

    with patch.object(service, "_get_repo_remote_url", return_value="https://github.com/Optirius/my-portfolio.git"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        success, msg = service.convert_repo_remote(repo_dir, "ssh")
        assert success is True
        assert "git@github.com:Optirius/my-portfolio.git" in msg