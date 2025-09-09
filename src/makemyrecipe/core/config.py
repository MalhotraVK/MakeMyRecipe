"""Configuration management for MakeMyRecipe application."""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    litellm_model: str = Field("claude-3-sonnet-20240229", alias="LITELLM_MODEL")

    # Database Configuration
    database_url: str = Field("sqlite:///./data/makemyrecipe.db", alias="DATABASE_URL")
    database_echo: bool = Field(False, alias="DATABASE_ECHO")

    # API Configuration
    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8000, alias="API_PORT")
    api_debug: bool = Field(False, alias="API_DEBUG")
    api_reload: bool = Field(True, alias="API_RELOAD")

    # Security
    secret_key: str = Field("change-me-in-production", alias="SECRET_KEY")
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8000"], alias="CORS_ORIGINS"
    )

    # Logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", alias="LOG_FORMAT"
    )

    # Application Settings
    app_name: str = Field("MakeMyRecipe", alias="APP_NAME")
    app_version: str = Field("0.1.0", alias="APP_VERSION")
    max_conversation_history: int = Field(50, alias="MAX_CONVERSATION_HISTORY")
    conversation_storage_path: str = Field(
        "./data/conversations", alias="CONVERSATION_STORAGE_PATH"
    )

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def __init__(self, **kwargs):
        """Initialize settings and create necessary directories."""
        super().__init__(**kwargs)
        self._create_directories()

    def _create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        # Create data directory
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)

        # Create conversation storage directory
        conv_dir = Path(self.conversation_storage_path)
        conv_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()