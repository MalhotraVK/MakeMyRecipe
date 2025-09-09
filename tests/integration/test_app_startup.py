"""Integration tests for application startup and configuration."""

import pytest
from fastapi.testclient import TestClient

from makemyrecipe.api.main import create_app
from makemyrecipe.core.config import Settings


class TestAppStartup:
    """Test cases for application startup and integration."""

    def test_app_creation(self):
        """Test that the application can be created successfully."""
        app = create_app()

        assert app is not None
        assert app.title == "MakeMyRecipe"
        assert app.version == "0.1.0"

    def test_app_with_test_client(self):
        """Test that the application works with TestClient."""
        app = create_app()

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200

    def test_cors_middleware(self, client: TestClient):
        """Test that CORS middleware is properly configured."""
        # Make a preflight request
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Should not return 405 Method Not Allowed
        assert response.status_code != 405

    def test_settings_integration(self):
        """Test that settings are properly integrated with the app."""
        settings = Settings()
        app = create_app()

        assert app.title == settings.app_name
        assert app.version == settings.app_version
