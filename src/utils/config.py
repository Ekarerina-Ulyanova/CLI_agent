"""
Configuration management for the Coding Agents system.
Uses Pydantic for validation and environment variable loading.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # GitHub Configuration
    github_token: str = Field(..., description="GitHub Personal Access Token")
    github_repository: str = Field(..., description="GitHub repository in format 'owner/repo'")
    github_owner: Optional[str] = Field(None, description="Repository owner username")
    
    # OpenRouter Configuration
    openrouter_api_key: str = Field(..., description="OpenRouter API key")
    openrouter_base_url: str = Field(
        "https://openrouter.ai/api/v1",
        description="OpenRouter API base URL"
    )
    openrouter_model: str = Field(
        "openai/gpt-4o-mini",
        description="OpenRouter model to use"
    )
    
    # Agent Configuration
    max_iterations: int = Field(
        5,
        ge=1,
        le=20,
        description="Maximum number of iteration cycles"
    )
    branch_prefix: str = Field(
        "agent/",
        description="Prefix for branches created by agent"
    )
    default_base_branch: str = Field(
        "main",
        description="Default base branch for PRs"
    )
    
    # Code Quality Tools
    use_ruff: bool = Field(True, description="Enable Ruff linter")
    use_black: bool = Field(True, description="Enable Black formatter")
    use_mypy: bool = Field(True, description="Enable MyPy type checker")
    use_pytest: bool = Field(True, description="Enable pytest")
    
    # Logging
    log_level: str = Field("INFO", description="Logging level")
    log_file: str = Field("agent.log", description="Log file path")
    
    @validator('github_repository')
    def validate_repository_format(cls, v):
        """Validate repository format is 'owner/repo'."""
        if '/' not in v:
            raise ValueError('Repository must be in format "owner/repo"')
        return v
    
    @validator('github_owner', pre=True, always=True)
    def set_github_owner(cls, v, values):
        """Set github_owner from repository if not provided."""
        if v is None and 'github_repository' in values:
            return values['github_repository'].split('/')[0]
        return v
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False


# Global settings instance
settings = Settings()