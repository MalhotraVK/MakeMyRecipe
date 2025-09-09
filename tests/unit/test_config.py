"""Unit tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest

from makemyrecipe.core.config import Settings


class TestSettings:
    """Test cases for Settings class."""

    def test_default_settings(self):
        """Test that default settings are loaded correctly."""
        settings = Settings()

        assert settings.app_name == "MakeMyRecipe"
        assert settings.app_version == "0.1.0"
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.litellm_model == "claude-3-5-sonnet-20241022"
        assert settings.max_conversation_history == 50

    def test_environment_variable_override(self):
        """Test that environment variables override default settings."""
        test_env = {
            "APP_NAME": "TestApp",
            "API_PORT": "9000",
            "MAX_CONVERSATION_HISTORY": "100",
        }

        # Set environment variables
        for key, value in test_env.items():
            os.environ[key] = value

        try:
            settings = Settings()
            assert settings.app_name == "TestApp"
            assert settings.api_port == 9000
            assert settings.max_conversation_history == 100
        finally:
            # Clean up environment variables
            for key in test_env:
                os.environ.pop(key, None)

    def test_directory_creation(self):
        """Test that necessary directories are created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            conv_path = temp_path / "test_conversations"

            os.environ["CONVERSATION_STORAGE_PATH"] = str(conv_path)

            try:
                settings = Settings()

                # Check that data directory exists
                assert Path("./data").exists()

                # Check that conversation storage directory exists
                assert conv_path.exists()

            finally:
                os.environ.pop("CONVERSATION_STORAGE_PATH", None)

    def test_cors_origins_parsing(self):
        """Test that CORS origins are parsed correctly."""
        settings = Settings()

        assert isinstance(settings.cors_origins, list)
        assert "http://localhost:3000" in settings.cors_origins
        assert "http://localhost:8000" in settings.cors_origins
