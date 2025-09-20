"""Configuration management for Render MCP Server"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Type-safe configuration with environment variable support"""

    # Required settings
    RENDER_API_KEY: str
    SERVICE_ID: str

    # Optional settings with defaults
    RENDER_BASE_URL: str = "https://api.render.com/v1"
    MAX_LOGS_PER_REQUEST: int = 100
    MAX_TOTAL_LOGS: int = 1000
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 5

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='forbid',
        case_sensitive=True
    )


# Global settings instance
settings = Settings()