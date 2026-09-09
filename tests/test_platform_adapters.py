from pathlib import Path
from github_account_manager.platform import (
    WindowsPlatformAdapter,
    MacOSPlatformAdapter,
    LinuxPlatformAdapter,
    get_platform_adapter,
)
from github_account_manager.services.app_integration_service import AppIntegrationService


def test_windows_platform_adapter():
    adapter = WindowsPlatformAdapter()
    assert adapter.os_name == "windows"
    assert adapter.get_system_font_family() == "Segoe UI"
    
    paths = adapter.get_ide_settings_paths("vscode")
    assert len(paths) >= 1
    assert any("Code" in str(p) and "settings.json" in str(p) for p in paths)


def test_macos_platform_adapter():
    adapter = MacOSPlatformAdapter()
    assert adapter.os_name == "macos"
    assert adapter.get_system_font_family() == ".SF NS Text"
    
    paths = adapter.get_ide_settings_paths("vscode")
    assert len(paths) >= 1
    assert any("Application Support" in str(p) and "settings.json" in str(p) for p in paths)


def test_linux_platform_adapter():
    adapter = LinuxPlatformAdapter()
    assert adapter.os_name == "linux"
    assert adapter.get_system_font_family() == "Ubuntu"
    
    paths = adapter.get_ide_settings_paths("vscode")
    assert len(paths) >= 1
    assert any(".config" in str(p) and "settings.json" in str(p) for p in paths)


def test_platform_factory_resolution():
    win = get_platform_adapter("win32")
    assert isinstance(win, WindowsPlatformAdapter)

    mac = get_platform_adapter("darwin")
    assert isinstance(mac, MacOSPlatformAdapter)

    lin = get_platform_adapter("linux")
    assert isinstance(lin, LinuxPlatformAdapter)


def test_app_integration_service_with_custom_adapter(tmp_path):
    class MockPlatform(LinuxPlatformAdapter):
        def get_ide_settings_paths(self, ide_id: str):
            return [tmp_path / ide_id / "settings.json"]

    mock_platform = MockPlatform()
    service = AppIntegrationService(platform=mock_platform)
    assert service.platform.os_name == "linux"

    success, msg = service.apply_isolation_to_app("vscode")
    assert success is True
    settings_file = tmp_path / "vscode" / "settings.json"
    assert settings_file.exists()
    assert "github.gitAuthentication" in settings_file.read_text(encoding="utf-8")


def test_macos_and_linux_dynamic_detection():
    mac = MacOSPlatformAdapter()
    mac_apps = mac.detect_installed_apps()
    assert isinstance(mac_apps, list)

    lin = LinuxPlatformAdapter()
    lin_apps = lin.detect_installed_apps()
    assert isinstance(lin_apps, list)

    assert isinstance(mac.get_ide_github_accounts(), list)
    assert isinstance(lin.get_ide_github_accounts(), list)


def test_linux_safe_xdg_path_resolution(monkeypatch):
    adapter = LinuxPlatformAdapter()

    # When XDG_CONFIG_HOME is empty string, should safely fall back to ~/.config
    monkeypatch.setenv("XDG_CONFIG_HOME", "")
    paths = adapter.get_ide_settings_paths("vscode")
    assert any(".config" in str(p) for p in paths)

    # When XDG_CONFIG_HOME is set to custom path
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config/path")
    paths_custom = adapter.get_ide_settings_paths("vscode")
    assert any("/custom/config/path" in str(p) for p in paths_custom)


def test_linux_git_credentials_parsing_and_deletion(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    git_creds = tmp_path / ".git-credentials"
    git_creds.write_text(
        "https://octocat:ghp_supersecretpattoken999@github.com\n"
        "https://workuser:ghp_worksecrettoken888@github.com\n"
        "https://gitlabuser:secret@gitlab.com\n",
        encoding="utf-8",
    )

    adapter = LinuxPlatformAdapter()
    creds = adapter.list_git_credentials()

    # Must find the 2 github credentials
    assert len(creds) == 2
    users = [c["user"] for c in creds]
    assert "octocat" in users
    assert "workuser" in users

    # CRITICAL: ensure secret tokens are NEVER present in user field
    for c in creds:
        assert "ghp_" not in c["user"]
        assert "secret" not in c["user"]

    # Target-aware deletion: delete only octocat
    target = "github.com (octocat) [~/.git-credentials]"
    assert adapter.delete_git_credential(target) is True

    # Check remaining credentials
    remaining = adapter.list_git_credentials()
    assert len(remaining) == 1
    assert remaining[0]["user"] == "workuser"

    # Gitlab credential untouched in file
    content = git_creds.read_text(encoding="utf-8")
    assert "gitlab.com" in content
    assert "workuser" in content
    assert "octocat" not in content