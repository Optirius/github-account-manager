"""SSH key generation, discovery, inspection, and live testing service with security hardening."""
import logging
import os
from pathlib import Path
import re
import subprocess
from typing import List, Optional, Tuple

from github_account_manager.config import DEFAULT_SSH_DIR
from github_account_manager.models import SSHKeyInfo

logger = logging.getLogger(__name__)

# Valid filename pattern for SSH keys (prevent directory traversal or argument injection)
KEY_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


class SSHService:
    def __init__(self, ssh_dir: Optional[Path] = None):
        self.ssh_dir = ssh_dir or DEFAULT_SSH_DIR
        self.ssh_dir.mkdir(parents=True, exist_ok=True)

    def list_keys(self) -> List[SSHKeyInfo]:
        """Discover existing SSH keys in the SSH directory."""
        keys: List[SSHKeyInfo] = []
        if not self.ssh_dir.exists():
            return keys

        pub_files = list(self.ssh_dir.glob("*.pub"))
        processed_privates = set()

        for pub in pub_files:
            priv_candidate = pub.with_suffix("")
            priv_path = str(priv_candidate) if priv_candidate.exists() else str(pub)
            processed_privates.add(priv_candidate.name)

            content = ""
            try:
                content = pub.read_text(encoding="utf-8").strip()
            except Exception:
                pass

            key_type, comment = self._parse_pub_content(content)
            fingerprint = self.get_fingerprint(pub)

            keys.append(
                SSHKeyInfo(
                    name=priv_candidate.name if priv_candidate.exists() else pub.stem,
                    private_key_path=priv_path,
                    public_key_path=str(pub),
                    key_type=key_type,
                    comment=comment,
                    fingerprint=fingerprint,
                    public_key_content=content,
                )
            )

        # Look for standalone private keys that don't have .pub
        for item in self.ssh_dir.iterdir():
            if item.is_file() and not item.name.endswith(".pub") and item.name not in ["known_hosts", "known_hosts.old", "config"]:
                if item.name not in processed_privates:
                    fingerprint = self.get_fingerprint(item)
                    keys.append(
                        SSHKeyInfo(
                            name=item.name,
                            private_key_path=str(item),
                            public_key_path=None,
                            key_type="Unknown",
                            comment=None,
                            fingerprint=fingerprint,
                            public_key_content=None,
                        )
                    )

        return keys

    def _parse_pub_content(self, content: str) -> Tuple[str, Optional[str]]:
        """Extract key algorithm and comment from public key string."""
        if not content:
            return "Unknown", None
        parts = content.split()
        key_type = "Unknown"
        comment = None
        if len(parts) >= 1:
            raw_type = parts[0].lower()
            if "ed25519" in raw_type:
                key_type = "ED25519"
            elif "rsa" in raw_type:
                key_type = "RSA"
            elif "ecdsa" in raw_type:
                key_type = "ECDSA"
            else:
                key_type = parts[0]
        if len(parts) >= 3:
            comment = " ".join(parts[2:])
        return key_type, comment

    def get_fingerprint(self, path: Path | str) -> Optional[str]:
        """Run ssh-keygen -l to retrieve fingerprint."""
        try:
            res = subprocess.run(
                ["ssh-keygen", "-l", "-f", str(path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception as e:
            logger.debug(f"Could not get fingerprint for {path}: {e}")
        return None

    def read_public_key(self, path_or_priv: Path | str) -> Optional[str]:
        """Read public key content given either private or public path."""
        p = Path(path_or_priv)
        if not p.name.endswith(".pub"):
            p = p.with_name(f"{p.name}.pub")

        if p.exists():
            try:
                return p.read_text(encoding="utf-8").strip()
            except Exception as e:
                logger.error(f"Error reading public key {p}: {e}")
        return None

    def generate_key(
        self,
        name: str,
        comment: str,
        key_type: str = "ed25519",
        bits: int = 4096,
        passphrase: str = "",
    ) -> Tuple[Path, Path]:
        """Generate a new SSH key pair safely without shell execution."""
        clean_name = name.strip()
        if not KEY_NAME_REGEX.match(clean_name):
            clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", clean_name)
        if not clean_name:
            clean_name = "id_ed25519_github"

        # Sanitize comment (strip newlines/quotes)
        clean_comment = re.sub(r"[\r\n\x00\"]", "", comment.strip())

        priv_path = self.ssh_dir / clean_name
        pub_path = self.ssh_dir / f"{clean_name}.pub"

        if priv_path.exists():
            raise FileExistsError(f"SSH key {priv_path.name} already exists in ~/.ssh/")

        clean_type = key_type.lower()
        if clean_type not in ["ed25519", "rsa", "ecdsa"]:
            clean_type = "ed25519"

        cmd = [
            "ssh-keygen",
            "-t",
            clean_type,
            "-C",
            clean_comment,
            "-f",
            str(priv_path),
            "-N",
            passphrase or "",
        ]
        if clean_type == "rsa":
            cmd.extend(["-b", str(max(2048, min(bits, 8192)))])

        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=15)
        if res.returncode != 0:
            raise RuntimeError(f"ssh-keygen failed: {res.stderr or res.stdout}")

        # Ensure restricted file permissions on Windows/Unix
        try:
            os.chmod(priv_path, 0o600)
        except Exception:
            pass

        return priv_path, pub_path

    def test_connection(
        self,
        private_key_path: Path | str,
        host: str = "git@github.com",
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Test SSH connection to GitHub.
        Returns: (success: bool, raw_output: str, authenticated_username: Optional[str])
        """
        priv_file = Path(private_key_path)
        if not priv_file.exists():
            return False, f"Private key file not found: {priv_file}", None

        # Clean host target
        clean_host = host.strip()
        if not clean_host or " " in clean_host:
            clean_host = "git@github.com"

        cmd = [
            "ssh",
            "-T",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            "-i",
            str(priv_file),
            clean_host,
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            output = (res.stderr + "\n" + res.stdout).strip()

            # GitHub returns exit code 1 even when auth succeeds
            match = re.search(r"Hi\s+([a-zA-Z0-9_\-]+)!\s+You've successfully authenticated", output, re.IGNORECASE)
            if match:
                username = match.group(1)
                return True, output, username

            if "successfully authenticated" in output.lower():
                return True, output, None

            if "permission denied" in output.lower():
                return False, f"Permission denied (publickey).\nThe key is not registered to a GitHub account or unauthorized.\n\n{output}", None

            return False, output or "No response from host.", None

        except subprocess.TimeoutExpired:
            return False, "SSH connection timed out (network unreachable or port 22 blocked).", None
        except Exception as e:
            return False, f"SSH test error: {e}", None
    def delete_key(self, path_or_name: Path | str) -> bool:
        """Delete private key and associated .pub file from disk."""
        p = Path(path_or_name)
        if not p.is_absolute():
            p = self.ssh_dir / p

        # Identify private and public paths
        priv_path = p.with_suffix("") if p.name.endswith(".pub") else p
        pub_path = priv_path.with_name(f"{priv_path.name}.pub")

        deleted_any = False
        if priv_path.exists():
            try:
                priv_path.unlink()
                deleted_any = True
            except Exception as e:
                logger.error(f"Failed to delete private key {priv_path}: {e}")

        if pub_path.exists():
            try:
                pub_path.unlink()
                deleted_any = True
            except Exception as e:
                logger.error(f"Failed to delete public key {pub_path}: {e}")

        return deleted_any