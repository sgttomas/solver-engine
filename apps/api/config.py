"""
SOLVER API Configuration - Doc 3 Section 12

Uses Pydantic Settings for environment variable management.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # Application Settings
    # =========================================================================
    app_name: str = Field(default="SOLVER API", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")

    # =========================================================================
    # PostgreSQL Settings
    # =========================================================================
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="solver", description="PostgreSQL user")
    postgres_password: str = Field(default="solver", description="PostgreSQL password")
    postgres_db: str = Field(default="solver", description="PostgreSQL database name")

    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL (async)."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def postgres_url_sync(self) -> str:
        """Construct synchronous PostgreSQL connection URL (for Alembic)."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # =========================================================================
    # LLM Provider Settings (Multi-provider support)
    # =========================================================================

    # Anthropic (Claude)
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514", description="Default Claude model")

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-5.2", description="Default OpenAI model")

    # Google (Gemini)
    google_api_key: Optional[str] = Field(default=None, description="Google AI API key")
    google_model: str = Field(default="gemini-1.5-pro", description="Default Gemini model")

    # Default provider
    default_llm_provider: str = Field(
        default="openai",
        description="Default LLM provider (anthropic, openai, google)"
    )

    # =========================================================================
    # Workflow Settings
    # =========================================================================
    default_gate_policy: str = Field(
        default="per_step",
        description="Default gate policy (none, per_step, end_of_pass)"
    )
    max_revision_attempts: int = Field(
        default=3,
        description="Maximum revision attempts before requiring human override"
    )

    # =========================================================================
    # Observability Settings
    # =========================================================================
    observability_provider: Optional[str] = Field(
        default=None,
        description="Observability provider (langsmith, langfuse, none)"
    )

    # LangSmith
    langsmith_api_key: Optional[str] = Field(default=None, description="LangSmith API key")
    langsmith_project: str = Field(default="solver", description="LangSmith project name")

    # Langfuse
    langfuse_public_key: Optional[str] = Field(default=None, description="Langfuse public key")
    langfuse_secret_key: Optional[str] = Field(default=None, description="Langfuse secret key")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", description="Langfuse host")

    # =========================================================================
    # API Settings
    # =========================================================================
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=1, description="Number of worker processes")

    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins"
    )

    # =========================================================================
    # Security Settings
    # =========================================================================
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    secret_key: str = Field(
        default="CHANGE_ME_IN_PRODUCTION",
        description="Secret key for signing tokens"
    )

    # =========================================================================
    # Validators
    # =========================================================================
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "staging", "production", "test"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @field_validator("default_gate_policy")
    @classmethod
    def validate_gate_policy(cls, v: str) -> str:
        """Validate gate policy value."""
        allowed = ["none", "per_step", "end_of_pass"]
        if v not in allowed:
            raise ValueError(f"Gate policy must be one of {allowed}")
        return v

    @field_validator("default_llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider value."""
        allowed = ["anthropic", "openai", "google"]
        if v not in allowed:
            raise ValueError(f"LLM provider must be one of {allowed}")
        return v

    # =========================================================================
    # Computed Properties
    # =========================================================================
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    @property
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.environment == "test"


# Global settings instance
settings = Settings()
