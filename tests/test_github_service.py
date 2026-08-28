from unittest.mock import patch, MagicMock
from github_account_manager.services.github_service import GitHubService


def test_lookup_user_by_username():
    service = GitHubService()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "login": "dev-user",
        "name": "Dev User",
        "email": "user@example.com",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345",
    }

    with patch("httpx.Client.get", return_value=mock_response):
        result = service.lookup_user_by_query("dev-user")
        assert result["success"] is True
        assert result["username"] == "dev-user"
        assert result["name"] == "Dev User"


def test_lookup_user_by_email():
    service = GitHubService()

    search_mock = MagicMock()
    search_mock.status_code = 200
    search_mock.json.return_value = {
        "total_count": 1,
        "items": [{"login": "dev-user"}]
    }

    user_mock = MagicMock()
    user_mock.status_code = 200
    user_mock.json.return_value = {
        "login": "dev-user",
        "name": "Dev User",
        "email": "user@example.com",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345",
    }

    def side_effect(url, **kwargs):
        if "search/users" in url:
            return search_mock
        return user_mock

    with patch("httpx.Client.get", side_effect=side_effect):
        result = service.lookup_user_by_query("user@example.com")
        assert result["success"] is True
        assert result["username"] == "dev-user"
        assert result["name"] == "Dev User"