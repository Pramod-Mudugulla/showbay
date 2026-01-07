from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, Field, HttpUrl, AfterValidator

# Convert HttpUrl to string for JSON serialization compatibility
def url_to_str(v: HttpUrl) -> str:
    return str(v)

class RepositoryCreateRequest(BaseModel):
    repo_url: Annotated[HttpUrl, AfterValidator(url_to_str)] = Field(
        ...,
        description="GitHub repository URL (e.g., https://github.com/owner/repo)",
        examples=["https://github.com/Pramod-Mudugulla/GhostShare"]
    )

class RepositoryCreateResponse(BaseModel):
    id: int
    full_name: str
    description: str | None
    stars: int
    forks: int
    open_issues: int
    primary_language: str | None
    html_url: str
    repo_created_at: datetime
    last_fetched_at: datetime

    class Config:
        from_attributes = True