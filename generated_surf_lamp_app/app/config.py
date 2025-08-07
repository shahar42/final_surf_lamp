```python
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    database_url: str
    database_pool_size: int = 10
    surfline_api_key: str
    weather_api_key: str
    secret_key: str
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    surf_update_interval_minutes: int = 15

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def log_level_enum(self) -> int:
        """Convert log_level string to logging module's integer level."""
        import logging
        return getattr(logging, self.log_level.upper())

    @property
    def surf_update_interval_seconds(self) -> int:
        """Convert surf_update_interval_minutes to seconds."""
        return self.surf_update_interval_minutes * 60

    @property
    def database_pool_min_size(self) -> int:
        """Ensure minimum pool size is at least 1."""
        return max(1, self.database_pool_size // 2)

    @property
    def database_pool_max_size(self) -> int:
        """Ensure maximum pool size is at least 2."""
        return max(2, self.database_pool_size)

settings = Settings()
```