from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = "GitHub Repository Insights Service"

    database_url: str = Field(..., env="DATABASE_URL")

    github_api_base_url: str = "https://api.github.com"
    github_token: str = Field(default=None, env="GITHUB_TOKEN")

    github_timeout_seconds: int = 10

    class Config:
        env_file = ".env"

settings = Settings()