"""Secure token storage service using OS Keyring / Windows Credential Manager with DPAPI fallback."""
import base64
import ctypes
from ctypes import wintypes
import logging
from pathlib import Path
from typing import Optional
import keyring
from github_account_manager.config import APP_ID, DATA_DIR

logger = logging.getLogger(__name__)


def mask_token(token: Optional[str]) -> str:
    """Safely mask a token for UI display or logs without exposing secret bytes."""
    if not token or not isinstance(token, str):
        return ""
    clean = token.strip()
    if len(clean) <= 8:
        return "•" * len(clean)
    return f"{clean[:4]}...{clean[-4:]}"


# --- Windows DPAPI Fallback Support ---
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


class DPAPIFallback:
    """Fallback encryption using Windows Data Protection API (DPAPI) tied to user logon."""

    @staticmethod
    def encrypt(data_str: str) -> Optional[str]:
        try:
            CryptProtectData = ctypes.windll.crypt32.CryptProtectData
            data_bytes = data_str.encode("utf-8")
            blob_in = DATA_BLOB(len(data_bytes), ctypes.cast(ctypes.create_string_buffer(data_bytes), ctypes.POINTER(ctypes.c_byte)))
            blob_out = DATA_BLOB()

            if CryptProtectData(ctypes.byref(blob_in), "GitHubMultiAccountManager", None, None, None, 0, ctypes.byref(blob_out)):
                encrypted_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                return base64.b64encode(encrypted_bytes).decode("utf-8")
        except Exception as e:
            logger.debug(f"DPAPI encrypt failed: {e}")
        return None

    @staticmethod
    def decrypt(enc_b64: str) -> Optional[str]:
        try:
            CryptUnprotectData = ctypes.windll.crypt32.CryptUnprotectData
            raw_encrypted = base64.b64decode(enc_b64.encode("utf-8"))
            blob_in = DATA_BLOB(len(raw_encrypted), ctypes.cast(ctypes.create_string_buffer(raw_encrypted), ctypes.POINTER(ctypes.c_byte)))
            blob_out = DATA_BLOB()

            if CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
                decrypted_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                return decrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.debug(f"DPAPI decrypt failed: {e}")
        return None


class KeyringService:
    def __init__(self, service_name: str = APP_ID):
        self.service_name = service_name
        self.fallback_file = DATA_DIR / ".vault.dat"

    def save_token(self, account_id: str, token: str) -> bool:
        """Securely store a GitHub Personal Access Token."""
        if not account_id or not token:
            return False

        clean_token = token.strip()
        try:
            keyring.set_password(self.service_name, account_id, clean_token)
            return True
        except Exception as e:
            logger.warning(f"Keyring backend write failed, using secure DPAPI fallback: {e}")
            return self._save_fallback(account_id, clean_token)

    def get_token(self, account_id: str) -> Optional[str]:
        """Retrieve stored token for an account."""
        if not account_id:
            return None

        try:
            val = keyring.get_password(self.service_name, account_id)
            if val:
                return val
        except Exception as e:
            logger.debug(f"Keyring read failed: {e}")

        # Check fallback
        return self._get_fallback(account_id)

    def delete_token(self, account_id: str) -> bool:
        """Delete stored token for an account."""
        if not account_id:
            return False

        success = True
        try:
            keyring.delete_password(self.service_name, account_id)
        except keyring.errors.PasswordDeleteError:
            pass
        except Exception as e:
            logger.debug(f"Keyring delete failed: {e}")
            success = False

        self._delete_fallback(account_id)
        return success

    # --- Secure Fallback Helpers ---

    def _save_fallback(self, account_id: str, token: str) -> bool:
        encrypted = DPAPIFallback.encrypt(token)
        if not encrypted:
            return False
        vault = self._read_vault()
        vault[account_id] = encrypted
        return self._write_vault(vault)

    def _get_fallback(self, account_id: str) -> Optional[str]:
        vault = self._read_vault()
        enc = vault.get(account_id)
        if enc:
            return DPAPIFallback.decrypt(enc)
        return None

    def _delete_fallback(self, account_id: str) -> None:
        vault = self._read_vault()
        if account_id in vault:
            del vault[account_id]
            self._write_vault(vault)

    def _read_vault(self) -> dict:
        if self.fallback_file.exists():
            try:
                import json
                return json.loads(self.fallback_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _write_vault(self, vault: dict) -> bool:
        try:
            import json
            self.fallback_file.write_text(json.dumps(vault), encoding="utf-8")
            return True
        except Exception:
            return False