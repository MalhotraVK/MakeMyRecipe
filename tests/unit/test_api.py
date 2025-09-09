"""Unit tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestAPIEndpoints:
    """Test cases for API endpoints."""

    def test_health_check(self, client: TestClient):
        """Test the health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data

    def test_root_endpoint(self, client: TestClient):
        """Test the root endpoint."""
        response = client.get("/")

        assert response.status_code == 200

        # The root endpoint serves HTML if static/index.html exists, otherwise JSON
        content_type = response.headers.get("content-type", "")

        if "text/html" in content_type:
            # If serving HTML file
            assert "<!DOCTYPE html>" in response.text
            assert "<title>" in response.text
        else:
            # If serving JSON response (when static files don't exist)
            data = response.json()
            assert "message" in data
            assert "version" in data
            assert data["docs"] == "/docs"

    def test_docs_endpoint(self, client: TestClient):
        """Test that the docs endpoint is accessible."""
        response = client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_endpoint(self, client: TestClient):
        """Test that the OpenAPI schema endpoint is accessible."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()

        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "MakeMyRecipe"
