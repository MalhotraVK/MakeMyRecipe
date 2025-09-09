"""Tests for chat API endpoints."""

import pytest
from fastapi.testclient import TestClient

from makemyrecipe.models.chat import ChatRequest, Conversation


def test_health_check(client: TestClient) -> None:
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data
    assert "version" in data


def test_root_endpoint(client: TestClient) -> None:
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data
    assert "websocket" in data


def test_send_chat_message_new_conversation(client: TestClient) -> None:
    """Test sending a chat message to create a new conversation."""
    request_data = {"message": "I want to make pasta", "user_id": "test_user_123"}

    response = client.post("/api/chat", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert "message" in data
    assert "conversation_id" in data
    assert "timestamp" in data
    assert data["conversation_id"] is not None


def test_send_chat_message_existing_conversation(client: TestClient) -> None:
    """Test sending a chat message to an existing conversation."""
    # First, create a conversation
    request_data = {"message": "I want to make pasta", "user_id": "test_user_123"}

    response = client.post("/api/chat", json=request_data)
    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]

    # Send another message to the same conversation
    request_data = {
        "message": "What ingredients do I need?",
        "user_id": "test_user_123",
        "conversation_id": conversation_id,
    }

    response = client.post("/api/chat", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["conversation_id"] == conversation_id


def test_send_chat_message_invalid_conversation(client: TestClient) -> None:
    """Test sending a chat message to a non-existent conversation."""
    request_data = {
        "message": "Hello",
        "user_id": "test_user_123",
        "conversation_id": "non_existent_id",
    }

    response = client.post("/api/chat", json=request_data)
    assert response.status_code == 404


def test_create_conversation(client: TestClient) -> None:
    """Test creating a new conversation."""
    response = client.post("/api/conversations?user_id=test_user_123")
    assert response.status_code == 200

    data = response.json()
    assert "conversation_id" in data
    assert "user_id" in data
    assert "system_prompt" in data
    assert "messages" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["user_id"] == "test_user_123"


def test_create_conversation_with_custom_prompt(client: TestClient) -> None:
    """Test creating a conversation with a custom system prompt."""
    custom_prompt = "You are a specialized Italian cuisine expert."
    response = client.post(
        f"/api/conversations?user_id=test_user_123&system_prompt={custom_prompt}"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["system_prompt"] == custom_prompt


def test_get_conversations(client: TestClient) -> None:
    """Test getting conversations for a user."""
    # Create a conversation first
    client.post("/api/conversations?user_id=test_user_123")

    response = client.get("/api/conversations?user_id=test_user_123")
    assert response.status_code == 200

    data = response.json()
    assert "conversations" in data
    assert "total" in data
    assert data["total"] >= 1


def test_get_conversations_with_limit(client: TestClient) -> None:
    """Test getting conversations with a limit."""
    # Create multiple conversations
    for i in range(3):
        client.post(f"/api/conversations?user_id=test_user_{i}")

    response = client.get("/api/conversations?user_id=test_user_0&limit=1")
    assert response.status_code == 200

    data = response.json()
    assert len(data["conversations"]) <= 1


def test_get_specific_conversation(client: TestClient) -> None:
    """Test getting a specific conversation by ID."""
    # Create a conversation
    response = client.post("/api/conversations?user_id=test_user_123")
    conversation_id = response.json()["conversation_id"]

    # Get the specific conversation
    response = client.get(f"/api/conversations/{conversation_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["conversation_id"] == conversation_id


def test_get_nonexistent_conversation(client: TestClient) -> None:
    """Test getting a non-existent conversation."""
    response = client.get("/api/conversations/nonexistent_id")
    assert response.status_code == 404


def test_delete_conversation(client: TestClient) -> None:
    """Test deleting a conversation."""
    # Create a conversation
    response = client.post("/api/conversations?user_id=test_user_123")
    conversation_id = response.json()["conversation_id"]

    # Delete the conversation
    response = client.delete(f"/api/conversations/{conversation_id}")
    assert response.status_code == 200

    # Verify it's deleted
    response = client.get(f"/api/conversations/{conversation_id}")
    assert response.status_code == 404


def test_delete_nonexistent_conversation(client: TestClient) -> None:
    """Test deleting a non-existent conversation."""
    response = client.delete("/api/conversations/nonexistent_id")
    assert response.status_code == 404


def test_chat_message_validation(client: TestClient) -> None:
    """Test chat message validation."""
    # Missing message
    request_data = {"user_id": "test_user_123"}
    response = client.post("/api/chat", json=request_data)
    assert response.status_code == 422

    # Missing user_id
    request_data = {"message": "Hello"}
    response = client.post("/api/chat", json=request_data)
    assert response.status_code == 422


def test_conversation_with_system_prompt(sample_conversation_data: dict) -> None:
    """Test that the sample conversation data includes system prompt."""
    assert "system_prompt" in sample_conversation_data
    assert sample_conversation_data["system_prompt"] is not None
    assert len(sample_conversation_data["system_prompt"]) > 0
