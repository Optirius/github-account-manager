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

    service = AppIntegrationService()
    with patch.object(AppIntegrationService, "vscode_settings_path", settings_file):
        status = service.get_vscode_status()
        assert status["installed"] is True
        assert status["is_isolated"] is False

        # Apply isolation
        success, msg = service.apply_vscode_isolation()
        assert success is True

        # Check updated settings
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        assert data["github.gitAuthentication"] is False
        assert data["git.terminalAuthentication"] is False

        status = service.get_vscode_status()
        assert status["is_isolated"] is True

        # Restore defaults
        success, msg = service.restore_vscode_defaults()
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