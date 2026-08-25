from unittest.mock import patch, MagicMock
from github_account_manager.services.github_service import GitHubService


def test_validate_token_success():
    service = GitHubService()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "login": "octocat",
        "name": "The Octocat",
        "email": "octocat@github.com",
        "avatar_url": "https://avatars.githubusercontent.com/u/583231",
    }
    mock_response.headers = {"x-oauth-scopes": "repo, user:email, admin:public_key"}

    with patch("httpx.Client.get", return_value=mock_response):
        result = service.validate_token("dummy_token")
        assert result["success"] is True
        assert result["username"] == "octocat"
        assert result["name"] == "The Octocat"
        assert result["email"] == "octocat@github.com"
        assert "admin:public_key" in result["scopes"]


def test_validate_token_unauthorized():
    service = GitHubService()

    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("httpx.Client.get", return_value=mock_response):
        result = service.validate_token("invalid_token")
        assert result["success"] is False
        assert "401" in result["error"]


def test_lookup_user_by_username():
    service = GitHubService()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "login": "tahmid95",
        "name": "Tahmid Hossain",
        "email": "tahmid95.hossain@gmail.com",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345",
    }

    with patch("httpx.Client.get", return_value=mock_response):
        result = service.lookup_user_by_query("tahmid95")
        assert result["success"] is True
        assert result["username"] == "tahmid95"
        assert result["name"] == "Tahmid Hossain"


def test_lookup_user_by_email():
    service = GitHubService()

    search_mock = MagicMock()
    search_mock.status_code = 200
    search_mock.json.return_value = {
        "total_count": 1,
        "items": [{"login": "tahmid95"}]
    }

    user_mock = MagicMock()
    user_mock.status_code = 200
    user_mock.json.return_value = {
        "login": "tahmid95",
        "name": "Tahmid Hossain",
        "email": "tahmid95.hossain@gmail.com",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345",
    }

    def side_effect(url, **kwargs):
        if "search/users" in url:
            return search_mock
        return user_mock

    with patch("httpx.Client.get", side_effect=side_effect):
        result = service.lookup_user_by_query("tahmid95.hossain@gmail.com")
        assert result["success"] is True
        assert result["username"] == "tahmid95"
        assert result["name"] == "Tahmid Hossain"


def test_upload_ssh_key():
    service = GitHubService()

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 123456,
        "title": "My PC Key",
        "created_at": "2026-08-25T00:00:00Z",
    }

    with patch("httpx.Client.post", return_value=mock_response):
        result = service.upload_ssh_key("token", "My PC Key", "ssh-ed25519 AAAAC3... test@example.com")
        assert result["success"] is True
        assert result["key_id"] == 123456