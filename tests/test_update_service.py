import json
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch
import zipfile

from github_account_manager.services.update_service import (
    UpdateInfo,
    UpdateService,
    parse_version_tuple,
)


def test_parse_version_tuple():
    assert parse_version_tuple("v0.1.20") == (0, 1, 20)
    assert parse_version_tuple("0.1.21") == (0, 1, 21)
    assert parse_version_tuple("v1.0") == (1, 0, 0)
    assert parse_version_tuple("v0.1.21") > parse_version_tuple("v0.1.20")
    assert parse_version_tuple("v0.2.0") > parse_version_tuple("v0.1.99")
    assert parse_version_tuple("v1.0.0") > parse_version_tuple("v0.9.9")
    assert not (parse_version_tuple("v0.1.20") > parse_version_tuple("v0.1.20"))


def test_check_for_updates_newer_available():
    service = UpdateService(current_version="v0.1.20")

    mock_release_payload = {
        "tag_name": "v0.1.21",
        "name": "GitHub Multi-Account Manager v0.1.21",
        "body": "### Features\n- Added In-App Updates\n- Multi-alias SSH support",
        "html_url": "https://github.com/Optirius/github-multi-account-manager/releases/tag/v0.1.21",
        "published_at": "2026-08-30T14:00:00Z",
        "assets": [
            {
                "name": "github-account-manager-windows-x64.zip",
                "browser_download_url": "https://github.com/Optirius/github-multi-account-manager/releases/download/v0.1.21/github-account-manager-windows-x64.zip",
                "size": 18500000,
            }
        ],
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(mock_release_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        with patch.object(service, "get_target_platform", return_value="windows"):
            info = service.check_for_updates()

            assert info is not None
            assert info.is_update_available is True
            assert info.latest_version == "v0.1.21"
            assert info.current_version == "v0.1.20"
            assert info.asset_name == "github-account-manager-windows-x64.zip"
            assert "In-App Updates" in info.release_notes


def test_check_for_updates_already_up_to_date():
    service = UpdateService(current_version="v0.1.21")

    mock_release_payload = {
        "tag_name": "v0.1.21",
        "name": "GitHub Multi-Account Manager v0.1.21",
        "body": "Latest release",
        "html_url": "https://github.com/Optirius/github-multi-account-manager/releases/tag/v0.1.21",
        "published_at": "2026-08-30T14:00:00Z",
        "assets": [],
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(mock_release_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        info = service.check_for_updates()
        assert info is not None
        assert info.is_update_available is False


def test_download_and_extract_asset(tmp_path):
    service = UpdateService()

    # Create mock zip asset with a dummy PE executable (>100KB with valid PE header)
    mock_zip = tmp_path / "test_update.zip"
    pe_header = bytearray(b"MZ" + b"\x00" * 58 + (64).to_bytes(4, "little") + b"PE\x00\x00")
    dummy_exe_content = bytes(pe_header) + (b"\x00" * 150_000)

    with zipfile.ZipFile(mock_zip, "w") as z:
        z.writestr("github-account-manager.exe", dummy_exe_content)

    update_info = UpdateInfo(
        current_version="v0.1.20",
        latest_version="v0.1.21",
        is_update_available=True,
        release_name="Release v0.1.21",
        release_notes="New release",
        html_url="https://github.com/Optirius/github-multi-account-manager",
        published_at="2026-08-30",
        asset_name="github-account-manager-windows-x64.zip",
        asset_download_url="https://github.com/Optirius/github-multi-account-manager/releases/download/v0.1.21/github-account-manager-windows-x64.zip",
        asset_size=len(mock_zip.read_bytes()),
    )

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Length": str(len(mock_zip.read_bytes()))}
        mock_resp.read.side_effect = [mock_zip.read_bytes(), b""]
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        progress_calls = []
        def progress(p, m):
            progress_calls.append((p, m))

        with patch.object(service, "get_target_platform", return_value="windows"):
            extracted = service.download_and_extract_asset(update_info, progress_callback=progress)

        assert extracted.exists()
        assert extracted.name == "github-account-manager.exe"
        assert extracted.read_bytes() == dummy_exe_content
        assert len(progress_calls) > 0


def test_download_and_extract_linux_asset(tmp_path):
    import tarfile
    service = UpdateService()

    # Create mock tar.gz asset with dummy ELF executable (>100KB with \x7fELF header)
    mock_tar = tmp_path / "github-account-manager-linux-x64.tar.gz"
    dummy_elf_content = b"\x7fELF" + (b"\x00" * 150_000)

    dummy_bin_path = tmp_path / "github-account-manager"
    dummy_bin_path.write_bytes(dummy_elf_content)

    with tarfile.open(mock_tar, "w:gz") as t:
        t.add(dummy_bin_path, arcname="github-account-manager")

    update_info = UpdateInfo(
        current_version="v0.1.20",
        latest_version="v0.1.21",
        is_update_available=True,
        release_name="Release v0.1.21",
        release_notes="New Linux release",
        html_url="https://github.com/Optirius/github-multi-account-manager",
        published_at="2026-08-30",
        asset_name="github-account-manager-linux-x64.tar.gz",
        asset_download_url="https://github.com/Optirius/github-multi-account-manager/releases/download/v0.1.21/github-account-manager-linux-x64.tar.gz",
        asset_size=len(mock_tar.read_bytes()),
    )

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Length": str(len(mock_tar.read_bytes()))}
        mock_resp.read.side_effect = [mock_tar.read_bytes(), b""]
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        with patch.object(service, "get_target_platform", return_value="linux"):
            extracted = service.download_and_extract_asset(update_info)

        assert extracted.exists()
        assert extracted.name == "github-account-manager"
        assert extracted.read_bytes() == dummy_elf_content


def test_is_secure_download_url():
    from github_account_manager.services.update_service import is_secure_download_url

    assert is_secure_download_url("https://github.com/Optirius/releases/asset.zip") is True
    assert is_secure_download_url("https://api.github.com/repos/Optirius/releases") is True
    assert is_secure_download_url("https://objects.githubusercontent.com/production/asset.zip") is True
    assert is_secure_download_url("https://release-assets.githubusercontent.com/asset.zip") is True
    assert is_secure_download_url("http://github.com/asset.zip") is False  # Insecure HTTP
    assert is_secure_download_url("https://malicious-site.com/asset.zip") is False  # Untrusted domain
    assert is_secure_download_url("https://github.com.evil.com/asset.zip") is False  # Phishing domain


def test_download_rejects_untrusted_url():
    from github_account_manager.services.update_service import SecurityError
    import pytest

    service = UpdateService()
    update_info = UpdateInfo(
        current_version="v0.1.20",
        latest_version="v0.1.21",
        is_update_available=True,
        release_name="Release v0.1.21",
        release_notes="New release",
        html_url="https://github.com",
        published_at="2026-08-30",
        asset_name="update.zip",
        asset_download_url="https://attacker-controlled-server.com/malicious.zip",
        asset_size=1000,
    )

    with pytest.raises(SecurityError, match="Untrusted download URL"):
        service.download_and_extract_asset(update_info)


def test_download_rejects_zipslip_traversal(tmp_path):
    from github_account_manager.services.update_service import SecurityError
    import pytest

    service = UpdateService()
    mock_zip = tmp_path / "zipslip.zip"
    with zipfile.ZipFile(mock_zip, "w") as z:
        z.writestr("../../Windows/System32/evil.exe", b"malicious payload")

    update_info = UpdateInfo(
        current_version="v0.1.20",
        latest_version="v0.1.21",
        is_update_available=True,
        release_name="Release v0.1.21",
        release_notes="New release",
        html_url="https://github.com",
        published_at="2026-08-30",
        asset_name="zipslip.zip",
        asset_download_url="https://github.com/Optirius/releases/zipslip.zip",
        asset_size=len(mock_zip.read_bytes()),
    )

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Length": str(len(mock_zip.read_bytes()))}
        mock_resp.read.side_effect = [mock_zip.read_bytes(), b""]
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        with pytest.raises(SecurityError, match="path traversal"):
            service.download_and_extract_asset(update_info)


def test_check_for_updates_macos_asset():
    service = UpdateService(current_version="v0.1.20")
    mock_payload = {
        "tag_name": "v0.1.21",
        "name": "Release v0.1.21",
        "body": "macOS update",
        "assets": [
            {
                "name": "github-account-manager-windows-x64.zip",
                "browser_download_url": "https://github.com/Optirius/releases/windows.zip",
                "size": 20000000,
            },
            {
                "name": "github-account-manager-macos.zip",
                "browser_download_url": "https://github.com/Optirius/releases/macos.zip",
                "size": 22000000,
            },
        ],
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        with patch.object(service, "get_target_platform", return_value="macos"):
            info = service.check_for_updates()
            assert info is not None
            assert info.is_update_available is True
            assert info.asset_name == "github-account-manager-macos.zip"


def test_check_for_updates_linux_asset():
    service = UpdateService(current_version="v0.1.20")
    mock_payload = {
        "tag_name": "v0.1.21",
        "name": "Release v0.1.21",
        "body": "Linux update",
        "assets": [
            {
                "name": "github-account-manager-linux-x64.tar.gz",
                "browser_download_url": "https://github.com/Optirius/releases/linux.tar.gz",
                "size": 19000000,
            },
            {
                "name": "github-account-manager-windows-x64.zip",
                "browser_download_url": "https://github.com/Optirius/releases/windows.zip",
                "size": 20000000,
            },
        ],
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        with patch.object(service, "get_target_platform", return_value="linux"):
            info = service.check_for_updates()
            assert info is not None
            assert info.is_update_available is True
            assert info.asset_name == "github-account-manager-linux-x64.tar.gz"


def test_verify_executable_format_linux_and_macos(tmp_path):
    from github_account_manager.services.update_service import verify_executable_format

    # Linux ELF executable
    elf_file = tmp_path / "test_elf"
    elf_file.write_bytes(b"\x7fELF" + (b"\x00" * 120_000))
    assert verify_executable_format(elf_file, "linux") is True
    assert verify_executable_format(elf_file, "windows") is False

    # macOS Mach-O 64-bit executable
    macho_file = tmp_path / "test_macho"
    macho_file.write_bytes(b"\xfe\xed\xfa\xcf" + (b"\x00" * 120_000))
    assert verify_executable_format(macho_file, "macos") is True
    assert verify_executable_format(macho_file, "linux") is False
