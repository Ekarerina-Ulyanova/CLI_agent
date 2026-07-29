"""
Configuration management for the Coding Agents system.
Uses Pydantic for validation and environment variable loading.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # GitHub Configuration
    # Empty defaults keep `--help` and static tooling usable without secrets.  The
    # application validates these values before it performs any remote operation.
    github_token: str = Field("", description="GitHub Personal Access Token")
    github_repository: str = Field("", description="GitHub repository in format 'owner/repo'")

    # OpenRouter Configuration
    openrouter_api_key: str = Field("", description="OpenRouter API key")
    openrouter_base_url: str = Field(
        "https://openrouter.ai/api/v1", description="OpenRouter API base URL"
    )
    openrouter_model: str = Field("openai/gpt-4o-mini", description="OpenRouter model to use")

    # Agent Configuration
    max_iterations: int = Field(5, ge=1, le=20, description="Maximum number of iteration cycles")
    branch_prefix: str = Field("agent/", description="Prefix for branches created by agent")
    default_base_branch: str = Field("main", description="Default base branch for PRs")
    issue_label: str = Field(
        "agent:implement", description="Label required before an issue is processed"
    )
    pr_label: str = Field("agent-generated", description="Label marking PRs created by this agent")
    review_pending_label: str = Field(
        "agent:review-pending", description="Label opting a PR into review"
    )
    reviewed_label: str = Field(
        "agent:reviewed", description="Label marking the current PR revision reviewed"
    )
    auto_merge: bool = Field(
        False, description="Allow automatic PR merge after all safeguards pass"
    )
    daemon_interval_seconds: int = Field(60, ge=10, le=3600)
    max_changed_files: int = Field(20, ge=1, le=100)
    max_file_size_bytes: int = Field(200_000, ge=1_000, le=2_000_000)

    # Code Quality Tools
    use_ruff: bool = Field(True, description="Enable Ruff linter")
    use_black: bool = Field(True, description="Enable Black formatter")
    use_mypy: bool = Field(True, description="Enable MyPy type checker")
    use_pytest: bool = Field(True, description="Enable pytest")

    # Logging
    log_level: str = Field("INFO", description="Logging level")
    log_file: str = Field("agent.log", description="Log file path")

    @field_validator("github_repository")
    @classmethod
    def validate_repository_format(cls, value: str) -> str:
        """Validate repository format is 'owner/repo'."""
        if value and (value.count("/") != 1 or any(not part for part in value.split("/"))):
            raise ValueError('Repository must be in format "owner/repo"')
        return value

    def validate_runtime(self) -> None:
        """Fail early with an actionable error before contacting external services."""
        missing = [
            name
            for name, value in {
                "GITHUB_TOKEN": self.github_token,
                "GITHUB_REPOSITORY": self.github_repository,
                "OPENROUTER_API_KEY": self.openrouter_api_key,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")


# Global settings instance
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process settings instance."""
    return Settings()


# Compatibility for existing imports. Values are validated in `init_services`,
# rather than as an import side effect.
settings = get_settings()
