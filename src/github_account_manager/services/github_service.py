"""GitHub REST API service for authentication, public lookup by username/email, and key management."""
import logging
import re
from typing import Any, Dict, List, Optional
import httpx
from github_account_manager.config import GITHUB_API_BASE

logger = logging.getLogger(__name__)


def redact_token_from_string(text: str, token: str) -> str:
    """Ensure raw token strings are never present in error messages or logs."""
    if not token or not text:
        return text
    clean_token = token.strip()
    if clean_token:
        text = text.replace(clean_token, "[REDACTED_TOKEN]")
    text = re.sub(r"(ghp_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{30,})", "[REDACTED_TOKEN]", text)
    return text


class GitHubService:
    def __init__(self, api_base: str = GITHUB_API_BASE, timeout: float = 10.0):
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

    def _headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "GitHub-Multi-Account-Manager/0.1.0",
        }
        if token and token.strip():
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    def lookup_user_by_query(self, query: str) -> Dict[str, Any]:
        """
        Search for GitHub user info using an Email or Username without requiring a token.
        Multi-strategy fallback ensures accurate profile discovery.
        """
        clean_q = query.strip()
        if not clean_q:
            return {"success": False, "error": "Search query is empty."}

        # If it's a token format, direct to validate_token
        if clean_q.startswith("ghp_") or clean_q.startswith("github_pat_") or len(clean_q) >= 36 and not ("@" in clean_q or " " in clean_q):
            return self.validate_token(clean_q)

        try:
            with httpx.Client(timeout=self.timeout, verify=True) as client:
                # Strategy 1: If input contains @, try search in email and search in users
                if "@" in clean_q:
                    # Search specifically in email
                    res = client.get(
                        f"{self.api_base}/search/users",
                        params={"q": f"{clean_q} in:email"},
                        headers=self._headers(),
                    )
                    if res.status_code == 200:
                        items = res.json().get("items", [])
                        if items:
                            return self._fetch_public_user(client, items[0]["login"], override_email=clean_q)

                    # General user search
                    res_gen = client.get(
                        f"{self.api_base}/search/users",
                        params={"q": clean_q},
                        headers=self._headers(),
                    )
                    if res_gen.status_code == 200:
                        items = res_gen.json().get("items", [])
                        if items:
                            return self._fetch_public_user(client, items[0]["login"], override_email=clean_q)

                    # Try user handle extracted from email prefix (e.g. "tahmid95" from "tahmid95.hossain@...")
                    email_handle = clean_q.split("@")[0].split(".")[0].strip()
                    if email_handle:
                        direct = client.get(f"{self.api_base}/users/{email_handle}", headers=self._headers())
                        if direct.status_code == 200:
                            data = direct.json()
                            return {
                                "success": True,
                                "username": data.get("login", ""),
                                "name": data.get("name") or data.get("login", ""),
                                "email": data.get("email") or clean_q,
                                "avatar_url": data.get("avatar_url", ""),
                                "raw": data,
                            }

                    # If not found on GitHub, return pre-populated email details
                    name_guess = clean_q.split("@")[0].replace(".", " ").title()
                    return {
                        "success": True,
                        "username": "",
                        "name": name_guess,
                        "email": clean_q,
                        "avatar_url": None,
                        "note": "Public GitHub account not indexed by email. Pre-filled name and email.",
                    }

                # Strategy 2: Direct username lookup
                clean_username = clean_q.lstrip("@")
                res = client.get(f"{self.api_base}/users/{clean_username}", headers=self._headers())
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "success": True,
                        "username": data.get("login", ""),
                        "name": data.get("name") or data.get("login", ""),
                        "email": data.get("email") or "",
                        "avatar_url": data.get("avatar_url", ""),
                        "raw": data,
                    }
                elif res.status_code == 404:
                    return {"success": False, "error": f"GitHub user '@{clean_username}' not found."}
                else:
                    return {"success": False, "error": f"GitHub API error: {res.status_code} - {res.text}"}

        except httpx.TimeoutException:
            return {"success": False, "error": "Connection to GitHub API timed out."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fetch_public_user(self, client: httpx.Client, username: str, override_email: str = "") -> Dict[str, Any]:
        """Fetch complete public user profile by handle."""
        res = client.get(f"{self.api_base}/users/{username}", headers=self._headers())
        if res.status_code == 200:
            data = res.json()
            return {
                "success": True,
                "username": data.get("login", ""),
                "name": data.get("name") or data.get("login", ""),
                "email": data.get("email") or override_email,
                "avatar_url": data.get("avatar_url", ""),
                "raw": data,
            }
        return {
            "success": True,
            "username": username,
            "name": username,
            "email": override_email,
            "avatar_url": None,
        }

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a GitHub Personal Access Token and fetch user profile details."""
        if not token or not token.strip():
            return {"success": False, "error": "Token is empty."}

        clean_token = token.strip()

        try:
            with httpx.Client(timeout=self.timeout, verify=True) as client:
                res = client.get(f"{self.api_base}/user", headers=self._headers(clean_token))
                if res.status_code == 200:
                    data = res.json()
                    scopes_header = res.headers.get("x-oauth-scopes", "")
                    scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]

                    # Fetch verified email if user:email scope is available
                    email = data.get("email") or ""
                    if not email and ("user:email" in scopes or "user" in scopes):
                        try:
                            email_res = client.get(
                                f"{self.api_base}/user/emails",
                                headers=self._headers(clean_token),
                            )
                            if email_res.status_code == 200:
                                emails = email_res.json()
                                for em in emails:
                                    if em.get("primary") and em.get("verified"):
                                        email = em.get("email", "")
                                        break
                                if not email and emails:
                                    email = emails[0].get("email", "")
                        except Exception as e:
                            logger.warning(f"Could not fetch user emails: {redact_token_from_string(str(e), clean_token)}")

                    return {
                        "success": True,
                        "username": data.get("login", ""),
                        "name": data.get("name") or data.get("login", ""),
                        "email": email,
                        "avatar_url": data.get("avatar_url", ""),
                        "scopes": scopes,
                        "token": clean_token,
                        "raw": data,
                    }
                elif res.status_code == 401:
                    return {
                        "success": False,
                        "error": "Invalid or expired token (HTTP 401 Unauthorized).",
                    }
                else:
                    msg = redact_token_from_string(f"GitHub API error: {res.status_code} - {res.text}", clean_token)
                    return {"success": False, "error": msg}
        except httpx.TimeoutException:
            return {"success": False, "error": "Connection to GitHub API timed out."}
        except Exception as e:
            return {"success": False, "error": redact_token_from_string(str(e), clean_token)}

    def list_user_ssh_keys(self, token: str) -> Dict[str, Any]:
        """Fetch SSH keys associated with the authenticated GitHub account."""
        clean_token = token.strip()
        try:
            with httpx.Client(timeout=self.timeout, verify=True) as client:
                res = client.get(f"{self.api_base}/user/keys", headers=self._headers(clean_token))
                if res.status_code == 200:
                    return {"success": True, "keys": res.json()}
                msg = redact_token_from_string(f"Failed to list keys: {res.status_code} - {res.text}", clean_token)
                return {"success": False, "error": msg}
        except Exception as e:
            return {"success": False, "error": redact_token_from_string(str(e), clean_token)}

    def upload_ssh_key(self, token: str, title: str, public_key_content: str) -> Dict[str, Any]:
        """Upload a public SSH key directly to GitHub."""
        clean_token = token.strip()
        clean_key = public_key_content.strip()
        if not clean_key:
            return {"success": False, "error": "Public key content is empty."}

        payload = {
            "title": title.strip() or "GitHub Account Manager Key",
            "key": clean_key,
        }

        try:
            with httpx.Client(timeout=self.timeout, verify=True) as client:
                res = client.post(
                    f"{self.api_base}/user/keys",
                    headers=self._headers(clean_token),
                    json=payload,
                )
                if res.status_code == 201:
                    data = res.json()
                    return {
                        "success": True,
                        "key_id": data.get("id"),
                        "title": data.get("title"),
                        "created_at": data.get("created_at"),
                    }
                elif res.status_code == 422:
                    return {
                        "success": False,
                        "error": "Key already exists on GitHub or key format is invalid.",
                    }
                msg = redact_token_from_string(f"GitHub API error: {res.status_code} - {res.text}", clean_token)
                return {"success": False, "error": msg}
        except Exception as e:
            return {"success": False, "error": redact_token_from_string(str(e), clean_token)}

    def delete_ssh_key(self, token: str, key_id: int) -> Dict[str, Any]:
        """Delete an SSH key from the GitHub account."""
        clean_token = token.strip()
        try:
            with httpx.Client(timeout=self.timeout, verify=True) as client:
                res = client.delete(
                    f"{self.api_base}/user/keys/{key_id}",
                    headers=self._headers(clean_token),
                )
                if res.status_code == 204:
                    return {"success": True}
                msg = redact_token_from_string(f"Failed to delete key: {res.status_code} - {res.text}", clean_token)
                return {"success": False, "error": msg}
        except Exception as e:
            return {"success": False, "error": redact_token_from_string(str(e), clean_token)}