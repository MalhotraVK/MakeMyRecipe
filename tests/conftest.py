"""Pytest configuration and fixtures for MakeMyRecipe tests."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from makemyrecipe.api.main import create_app
from makemyrecipe.core.config import Settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings with temporary directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Override settings for testing
        test_env = {
            "DATABASE_URL": f"sqlite:///{temp_path}/test.db",
            "CONVERSATION_STORAGE_PATH": str(temp_path / "conversations"),
            "API_DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
        }

        # Set environment variables
        for key, value in test_env.items():
            os.environ[key] = value

        settings = Settings()
        yield settings

        # Clean up environment variables
        for key in test_env:
            os.environ.pop(key, None)


@pytest.fixture
def client(test_settings: Settings) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_conversation_data() -> dict:
    """Sample conversation data for testing."""
    return {
        "user_id": "test_user_123",
        "conversation_id": "conv_456",
        "messages": [
            {
                "role": "user",
                "content": "I want to make pasta with tomatoes",
                "timestamp": "2024-01-01T12:00:00Z",
            },
            {
                "role": "assistant",
                "content": "I can help you with a delicious pasta recipe!",
                "timestamp": "2024-01-01T12:00:05Z",
            },
        ],
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:05Z",
    }
