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