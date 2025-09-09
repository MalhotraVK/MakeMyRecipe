"""Tests for chat API with citations support."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.makemyrecipe.api.main import app
from src.makemyrecipe.models.chat import ChatMessage


class TestChatAPICitations:
    """Test cases for chat API with citations support."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_chat_request(self):
        """Create a sample chat request."""
        return {"message": "I want to make pasta carbonara", "user_id": "test-user-123"}

    @pytest.fixture
    def sample_citations(self):
        """Create sample citations."""
        return [
            {
                "title": "Authentic Pasta Carbonara Recipe",
                "url": "https://example.com/carbonara",
                "snippet": (
                    "Traditional Italian carbonara with eggs, cheese, and pancetta"
                ),
            },
            {
                "title": "Italian Cooking Techniques",
                "url": "https://example.com/italian-cooking",
                "snippet": "Master the art of Italian cuisine",
            },
        ]

    @patch("src.makemyrecipe.services.llm_service.llm_service")
    def test_chat_endpoint_returns_citations(
        self, mock_llm_service, client, sample_chat_request, sample_citations
    ):
        """Test that chat endpoint returns citations."""
        # Mock the LLM service to return response with citations
        mock_llm_service.generate_response_with_citations.return_value = (
            "Here's a great carbonara recipe with authentic Italian techniques!",
            sample_citations,
        )

        response = client.post("/api/chat", json=sample_chat_request)

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "conversation_id" in data
        assert "citations" in data
        assert "timestamp" in data

        # Check citations structure
        citations = data["citations"]
        assert len(citations) == 2

        for citation in citations:
            assert "title" in citation
            assert "url" in citation
            assert "snippet" in citation

        assert citations[0]["title"] == "Authentic Pasta Carbonara Recipe"
        assert citations[0]["url"] == "https://example.com/carbonara"

    @patch("src.makemyrecipe.services.llm_service.llm_service")
    def test_chat_endpoint_empty_citations(
        self, mock_llm_service, client, sample_chat_request
    ):
        """Test chat endpoint with empty citations."""
        # Mock the LLM service to return response without citations
        mock_llm_service.generate_response_with_citations.return_value = (
            "Here's a simple pasta recipe.",
            [],
        )

        response = client.post("/api/chat", json=sample_chat_request)

        assert response.status_code == 200
        data = response.json()

        assert "citations" in data
        assert data["citations"] == []

    @patch("src.makemyrecipe.services.llm_service.llm_service")
    def test_chat_endpoint_with_conversation_id(
        self, mock_llm_service, client, sample_citations
    ):
        """Test chat endpoint with existing conversation."""
        # First, create a conversation
        create_response = client.post("/api/conversations?user_id=test-user-123")
        assert create_response.status_code == 200
        conversation_id = create_response.json()["conversation_id"]

        # Mock the LLM service
        mock_llm_service.generate_response_with_citations.return_value = (
            "Here's another great recipe!",
            sample_citations,
        )

        # Send message to existing conversation
        chat_request = {
            "message": "What about dessert recipes?",
            "user_id": "test-user-123",
            "conversation_id": conversation_id,
        }

        response = client.post("/api/chat", json=chat_request)

        assert response.status_code == 200
        data = response.json()

        assert data["conversation_id"] == conversation_id
        assert len(data["citations"]) == 2

    @patch("src.makemyrecipe.services.llm_service.llm_service")
    def test_chat_endpoint_handles_citation_conversion_errors(
        self, mock_llm_service, client, sample_chat_request
    ):
        """Test that chat endpoint handles citation conversion errors gracefully."""
        # Mock the LLM service to return malformed citations
        mock_llm_service.generate_response_with_citations.return_value = (
            "Here's a recipe.",
            [
                {"title": "Good Recipe"},  # Missing url and snippet
                {"url": "https://example.com"},  # Missing title and snippet
                None,  # Invalid citation
                {
                    "title": "Complete Recipe",
                    "url": "https://example.com/complete",
                    "snippet": "Full recipe",
                },
            ],
        )

        response = client.post("/api/chat", json=sample_chat_request)

        assert response.status_code == 200
        data = response.json()

        # Should handle malformed citations gracefully
        citations = data["citations"]
        assert len(citations) == 4  # All citations should be processed

        # Check that missing fields are handled
        assert citations[0]["title"] == "Good Recipe"
        assert citations[0]["url"] == ""
        assert citations[0]["snippet"] == ""

        assert citations[1]["title"] == ""
        assert citations[1]["url"] == "https://example.com"
        assert citations[1]["snippet"] == ""

    def test_chat_endpoint_invalid_request(self, client):
        """Test chat endpoint with invalid request."""
        invalid_request = {
            "message": "",  # Empty message
            "user_id": "",  # Empty user ID
        }

        response = client.post("/api/chat", json=invalid_request)

        # Should return validation error
        assert response.status_code == 422

    def test_chat_endpoint_missing_fields(self, client):
        """Test chat endpoint with missing required fields."""
        incomplete_request = {
            "message": "Hello"
            # Missing user_id
        }

        response = client.post("/api/chat", json=incomplete_request)

        # Should return validation error
        assert response.status_code == 422

    @patch("src.makemyrecipe.services.llm_service.llm_service")
    def test_chat_endpoint_llm_service_exception(
        self, mock_llm_service, client, sample_chat_request
    ):
        """Test chat endpoint when LLM service raises an exception."""
        # Mock the LLM service to raise an exception
        mock_llm_service.generate_response_with_citations.side_effect = Exception(
            "LLM service error"
        )

        response = client.post("/api/chat", json=sample_chat_request)

        # Should return internal server error
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    @patch("src.makemyrecipe.services.chat_service.chat_service")
    def test_chat_endpoint_conversation_not_found(self, mock_chat_service, client):
        """Test chat endpoint with non-existent conversation ID."""
        mock_chat_service.get_conversation.return_value = None

        chat_request = {
            "message": "Hello",
            "user_id": "test-user-123",
            "conversation_id": "non-existent-id",
        }

        response = client.post("/api/chat", json=chat_request)

        # Should return not found error
        assert response.status_code == 404
        assert "Conversation not found" in response.json()["detail"]


@pytest.mark.integration
class TestChatAPICitationsIntegration:
    """Integration tests for chat API with citations."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_full_conversation_workflow_with_citations(self, client):
        """Test complete conversation workflow with citations."""
        # Create a new conversation
        create_response = client.post(
            "/api/conversations?user_id=test-user-integration"
        )
        assert create_response.status_code == 200
        conversation_id = create_response.json()["conversation_id"]

        # Send first message (recipe query)
        chat_request_1 = {
            "message": "I want to make Italian pasta",
            "user_id": "test-user-integration",
            "conversation_id": conversation_id,
        }

        response_1 = client.post("/api/chat", json=chat_request_1)
        assert response_1.status_code == 200

        data_1 = response_1.json()
        assert data_1["conversation_id"] == conversation_id
        assert "message" in data_1
        assert "citations" in data_1

        # Send follow-up message
        chat_request_2 = {
            "message": "What about vegetarian options?",
            "user_id": "test-user-integration",
            "conversation_id": conversation_id,
        }

        response_2 = client.post("/api/chat", json=chat_request_2)
        assert response_2.status_code == 200

        data_2 = response_2.json()
        assert data_2["conversation_id"] == conversation_id

        # Get conversation history
        history_response = client.get(f"/api/conversations/{conversation_id}")
        assert history_response.status_code == 200

        history_data = history_response.json()
        assert len(history_data["messages"]) == 4  # 2 user + 2 assistant messages

        # Verify message order
        messages = history_data["messages"]
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "I want to make Italian pasta"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "What about vegetarian options?"
        assert messages[3]["role"] == "assistant"

    def test_recipe_vs_non_recipe_queries(self, client):
        """Test that recipe and non-recipe queries are handled appropriately."""
        # Create conversation
        create_response = client.post("/api/conversations?user_id=test-user-queries")
        conversation_id = create_response.json()["conversation_id"]

        # Recipe query
        recipe_request = {
            "message": "How do I make chocolate cake?",
            "user_id": "test-user-queries",
            "conversation_id": conversation_id,
        }

        recipe_response = client.post("/api/chat", json=recipe_request)
        assert recipe_response.status_code == 200
        recipe_data = recipe_response.json()

        # Non-recipe query
        general_request = {
            "message": "What's the weather like?",
            "user_id": "test-user-queries",
            "conversation_id": conversation_id,
        }

        general_response = client.post("/api/chat", json=general_request)
        assert general_response.status_code == 200
        general_data = general_response.json()

        # Both should succeed and return appropriate responses
        assert "message" in recipe_data
        assert "citations" in recipe_data
        assert "message" in general_data
        assert "citations" in general_data
