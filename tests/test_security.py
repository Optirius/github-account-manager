import sys
import pytest
from github_account_manager.models import Account, FolderMapping, sanitize_git_string
from github_account_manager.services.github_service import redact_token_from_string
from github_account_manager.services.keyring_service import mask_token, DPAPIFallback, LinuxVaultFallback, KeyringService
from github_account_manager.services.ssh_service import SSHService


def test_git_string_sanitization():
    # Test newline injection prevention
    injected_str = "My Name\n[core]\n\tsshCommand = calc.exe"
    sanitized = sanitize_git_string(injected_str)
    assert "\n" not in sanitized
    assert "\r" not in sanitized
    assert "\x00" not in sanitized
    assert sanitized == "My Name[core]\tsshCommand = calc.exe"


def test_account_model_injection_resilience():
    acc = Account(
        name="Personal\n[evil]",
        email="test@example.com\r\n[attack]",
        git_name="Hacker\nName",
    )
    assert "\n" not in acc.name
    assert "\r" not in acc.email
    assert "\n" not in acc.git_name


def test_token_redaction():
    token = "ghp_1234567890abcdef1234567890abcdef"
    error_msg = f"HTTP 401: Invalid token {token} provided."
    redacted = redact_token_from_string(error_msg, token)
    assert token not in redacted
    assert "[REDACTED_TOKEN]" in redacted


def test_mask_token():
    assert mask_token("ghp_1234567890abcdef") == "ghp_...cdef"
    assert mask_token("") == ""
    assert mask_token(None) == ""


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-specific")
def test_dpapi_fallback_encryption():
    secret = "ghp_super_secret_pat_token_value_12345"
    encrypted = DPAPIFallback.encrypt(secret)
    assert encrypted is not None
    assert encrypted != secret

    decrypted = DPAPIFallback.decrypt(encrypted)
    assert decrypted == secret


def test_cross_platform_vault_fallback_encryption():
    secret = "ghp_linux_test_pat_token_value_98765"
    encrypted = LinuxVaultFallback.encrypt(secret)
    assert encrypted is not None
    assert encrypted != secret

    decrypted = LinuxVaultFallback.decrypt(encrypted)
    assert decrypted == secret


def test_keyring_service_fallback_roundtrip(tmp_path, monkeypatch):
    import keyring

    def failing_set_password(*args, **kwargs):
        raise RuntimeError("Keyring daemon simulated failure")

    def failing_get_password(*args, **kwargs):
        return None

    def failing_delete_password(*args, **kwargs):
        raise RuntimeError("Keyring daemon simulated failure")

    monkeypatch.setattr(keyring, "set_password", failing_set_password)
    monkeypatch.setattr(keyring, "get_password", failing_get_password)
    monkeypatch.setattr(keyring, "delete_password", failing_delete_password)

    service = KeyringService(service_name="test-service")
    service.fallback_file = tmp_path / ".vault.dat"

    # Save token via fallback
    ok = service.save_token("test-account-1", "ghp_mock_token_12345")
    assert ok is True
    assert service.fallback_file.exists()

    # Retrieve token via fallback
    retrieved = service.get_token("test-account-1")
    assert retrieved == "ghp_mock_token_12345"

    # Delete token
    assert service.delete_token("test-account-1") is True
    assert service.get_token("test-account-1") is None