from github_account_manager.models import Account, FolderMapping, sanitize_git_string
from github_account_manager.services.github_service import redact_token_from_string
from github_account_manager.services.keyring_service import mask_token, DPAPIFallback
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


def test_dpapi_fallback_encryption():
    secret = "ghp_super_secret_pat_token_value_12345"
    encrypted = DPAPIFallback.encrypt(secret)
    assert encrypted is not None
    assert encrypted != secret

    decrypted = DPAPIFallback.decrypt(encrypted)
    assert decrypted == secret