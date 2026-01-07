from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


def parse_github_repo_url(repo_url: str) -> tuple[str, str]:
    """Parse a GitHub repository URL and extract owner and repo name."""
    # Handle both string and HttpUrl types
    url_str = str(repo_url)
    parsed = urlparse(url_str)
    
    if parsed.netloc != "github.com":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid repository URL. Only GitHub repositories are supported.",
        )
    path_parts = parsed.path.strip("/").split("/")

    if len(path_parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid repository URL format. Expected: https://github.com/owner/repo",
        )

    return path_parts[0], path_parts[1]


async def fetch_repository_from_github(owner: str, repo: str) -> dict:
    """Fetch repository data from GitHub API."""
    url = f'{settings.github_api_base_url}/repos/{owner}/{repo}'

    headers = {}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    timeout = httpx.Timeout(settings.github_timeout_seconds)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to connect to GitHub API: {str(e)}",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository '{owner}/{repo}' not found on GitHub",
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API error: {response.status_code}",
            )

        return response.json()


def map_github_response(data: dict) -> dict:
    """Map GitHub API response to our Repository model fields."""
    return {
        "owner": data["owner"]["login"],
        "repo_name": data["name"],
        "full_name": data["full_name"],
        "description": data.get("description"),
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "primary_language": data.get("language"),
        "html_url": data["html_url"],
        "repo_created_at": datetime.fromisoformat(
            data["created_at"].replace("Z", "+00:00")
        ),
        "last_fetched_at": datetime.now(timezone.utc),
    }


async def get_repository_data(repo_url: str) -> dict:
    """Main function to get repository data from a GitHub URL."""
    owner, repo = parse_github_repo_url(repo_url)
    github_data = await fetch_repository_from_github(owner, repo)
    return map_github_response(github_data)
