"""Unit tests for GitHub service."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone

from fastapi import HTTPException

from app.services.github_service import (
    parse_github_repo_url,
    fetch_repository_from_github,
    map_github_response,
    get_repository_data,
)


class TestParseGitHubRepoUrl:
    """Tests for parse_github_repo_url function."""

    def test_valid_github_url(self):
        """Test parsing a valid GitHub URL."""
        owner, repo = parse_github_repo_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_valid_github_url_with_trailing_slash(self):
        """Test parsing a valid GitHub URL with trailing slash."""
        owner, repo = parse_github_repo_url("https://github.com/owner/repo/")
        assert owner == "owner"
        assert repo == "repo"

    def test_valid_github_url_with_extra_path(self):
        """Test parsing a GitHub URL with extra path segments."""
        owner, repo = parse_github_repo_url("https://github.com/owner/repo/tree/main")
        assert owner == "owner"
        assert repo == "repo"

    def test_invalid_domain(self):
        """Test that non-GitHub URLs raise an error."""
        with pytest.raises(HTTPException) as exc_info:
            parse_github_repo_url("https://gitlab.com/owner/repo")
        assert exc_info.value.status_code == 422
        assert "Only GitHub repositories are supported" in exc_info.value.detail

    def test_invalid_url_format_missing_repo(self):
        """Test that URLs without repo name raise an error."""
        with pytest.raises(HTTPException) as exc_info:
            parse_github_repo_url("https://github.com/owner")
        assert exc_info.value.status_code == 422
        assert "Invalid repository URL format" in exc_info.value.detail

    def test_invalid_url_format_empty_path(self):
        """Test that URLs without path raise an error."""
        with pytest.raises(HTTPException) as exc_info:
            parse_github_repo_url("https://github.com/")
        assert exc_info.value.status_code == 422


class TestMapGitHubResponse:
    """Tests for map_github_response function."""

    def test_maps_all_fields_correctly(self):
        """Test that GitHub API response is mapped correctly."""
        github_data = {
            "owner": {"login": "testowner"},
            "name": "testrepo",
            "full_name": "testowner/testrepo",
            "description": "A test repository",
            "stargazers_count": 100,
            "forks_count": 50,
            "open_issues_count": 10,
            "language": "Python",
            "html_url": "https://github.com/testowner/testrepo",
            "created_at": "2024-01-01T00:00:00Z",
        }

        result = map_github_response(github_data)

        assert result["owner"] == "testowner"
        assert result["repo_name"] == "testrepo"
        assert result["full_name"] == "testowner/testrepo"
        assert result["description"] == "A test repository"
        assert result["stars"] == 100
        assert result["forks"] == 50
        assert result["open_issues"] == 10
        assert result["primary_language"] == "Python"
        assert result["html_url"] == "https://github.com/testowner/testrepo"
        assert isinstance(result["repo_created_at"], datetime)
        assert isinstance(result["last_fetched_at"], datetime)

    def test_handles_null_description(self):
        """Test that null description is handled correctly."""
        github_data = {
            "owner": {"login": "testowner"},
            "name": "testrepo",
            "full_name": "testowner/testrepo",
            "description": None,
            "stargazers_count": 0,
            "forks_count": 0,
            "open_issues_count": 0,
            "language": None,
            "html_url": "https://github.com/testowner/testrepo",
            "created_at": "2024-01-01T00:00:00Z",
        }

        result = map_github_response(github_data)

        assert result["description"] is None
        assert result["primary_language"] is None


class TestFetchRepositoryFromGitHub:
    """Tests for fetch_repository_from_github function."""

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        """Test successful API fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "testrepo"}

        with patch("app.services.github_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await fetch_repository_from_github("owner", "repo")
            assert result == {"name": "testrepo"}

    @pytest.mark.asyncio
    async def test_repo_not_found(self):
        """Test 404 response from GitHub."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("app.services.github_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            with pytest.raises(HTTPException) as exc_info:
                await fetch_repository_from_github("owner", "nonexistent")
            assert exc_info.value.status_code == 404
            assert "not found on GitHub" in exc_info.value.detail


class TestGetRepositoryData:
    """Tests for get_repository_data function."""

    @pytest.mark.asyncio
    async def test_integration(self):
        """Test the full flow from URL to mapped data."""
        github_data = {
            "owner": {"login": "testowner"},
            "name": "testrepo",
            "full_name": "testowner/testrepo",
            "description": "Test",
            "stargazers_count": 10,
            "forks_count": 5,
            "open_issues_count": 2,
            "language": "Python",
            "html_url": "https://github.com/testowner/testrepo",
            "created_at": "2024-01-01T00:00:00Z",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = github_data

        with patch("app.services.github_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await get_repository_data("https://github.com/testowner/testrepo")

            assert result["owner"] == "testowner"
            assert result["repo_name"] == "testrepo"
            assert result["stars"] == 10
