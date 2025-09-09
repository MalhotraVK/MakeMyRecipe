"""Tests for WebSocket functionality."""

import json
from typing import Generator

import pytest
from fastapi.testclient import TestClient


def test_websocket_connection(client: TestClient) -> None:
    """Test WebSocket connection establishment."""
    with client.websocket_connect("/ws/chat/test_user") as websocket:
        # Should receive welcome message
        data = websocket.receive_text()
        message = json.loads(data)

        assert message["type"] == "status"
        assert "Connected to MakeMyRecipe chat" in message["data"]["message"]
        assert message["data"]["user_id"] == "test_user"


def test_websocket_chat_message(client: TestClient) -> None:
    """Test sending a chat message via WebSocket."""
    with client.websocket_connect("/ws/chat/test_user") as websocket:
        # Receive welcome message
        websocket.receive_text()

        # Send a chat message
        chat_message = {"type": "chat", "message": "I want to make pasta"}
        websocket.send_text(json.dumps(chat_message))

        # Should receive user message confirmation
        data = websocket.receive_text()
        user_msg = json.loads(data)
        assert user_msg["type"] == "user_message"
        assert user_msg["data"]["message"] == "I want to make pasta"
        assert user_msg["data"]["role"] == "user"
        assert "conversation_id" in user_msg["data"]

        # Should receive assistant response
        data = websocket.receive_text()
        assistant_msg = json.loads(data)
        assert assistant_msg["type"] == "assistant_message"
        assert assistant_msg["data"]["role"] == "assistant"
        assert len(assistant_msg["data"]["message"]) > 0


def test_websocket_ping_pong(client: TestClient) -> None:
    """Test WebSocket ping/pong functionality."""
    with client.websocket_connect("/ws/chat/test_user") as websocket:
        # Receive welcome message
        websocket.receive_text()

        # Send ping
        ping_message = {"type": "ping"}
        websocket.send_text(json.dumps(ping_message))

        # Should receive pong
        data = websocket.receive_text()
        pong_msg = json.loads(data)
        assert pong_msg["type"] == "pong"
        assert pong_msg["data"]["message"] == "pong"


def test_websocket_invalid_json(client: TestClient) -> None:
    """Test WebSocket with invalid JSON."""
    with client.websocket_connect("/ws/chat/test_user") as websocket:
        # Receive welcome message
        websocket.receive_text()

        # Send invalid JSON
        websocket.send_text("invalid json")

        # Should receive error message
        data = websocket.receive_text()
        error_msg = json.loads(data)
        assert error_msg["type"] == "error"
        assert "Invalid JSON format" in error_msg["data"]["error"]


def test_websocket_empty_message(client: TestClient) -> None:
    """Test WebSocket with empty chat message."""
    with client.websocket_connect("/ws/chat/test_user") as websocket:
        # Receive welcome message
        websocket.receive_text()

        # Send empty message
        chat_message = {"type": "chat", "message": ""}
        websocket.send_text(json.dumps(chat_message))

        # Should receive error message
        data = websocket.receive_text()
        error_msg = json.loads(data)
        assert error_msg["type"] == "error"
        assert "Message cannot be empty" in error_msg["data"]["error"]


def test_websocket_unknown_message_type(client: TestClient) -> None:
    """Test WebSocket with unknown message type."""
    with client.websocket_connect("/ws/chat/test_user") as websocket:
        # Receive welcome message
        websocket.receive_text()

        # Send unknown message type
        unknown_message = {"type": "unknown_type", "data": "some data"}
        websocket.send_text(json.dumps(unknown_message))

        # Should receive error message
        data = websocket.receive_text()
        error_msg = json.loads(data)
        assert error_msg["type"] == "error"
        assert "Unknown message type" in error_msg["data"]["error"]


def test_websocket_existing_conversation(client: TestClient) -> None:
    """Test WebSocket with existing conversation ID."""
    # First create a conversation via REST API
    response = client.post("/api/conversations?user_id=test_user")
    conversation_id = response.json()["conversation_id"]

    with client.websocket_connect("/ws/chat/test_user") as websocket:
        # Receive welcome message
        websocket.receive_text()

        # Send message with existing conversation ID
        chat_message = {
            "type": "chat",
            "message": "Continue our conversation",
            "conversation_id": conversation_id,
        }
        websocket.send_text(json.dumps(chat_message))

        # Should receive user message confirmation
        data = websocket.receive_text()
        user_msg = json.loads(data)
        assert user_msg["data"]["conversation_id"] == conversation_id

        # Should receive assistant response
        data = websocket.receive_text()
        assistant_msg = json.loads(data)
        assert assistant_msg["data"]["conversation_id"] == conversation_id


def test_websocket_nonexistent_conversation(client: TestClient) -> None:
    """Test WebSocket with non-existent conversation ID."""
    with client.websocket_connect("/ws/chat/test_user") as websocket:
        # Receive welcome message
        websocket.receive_text()

        # Send message with non-existent conversation ID
        chat_message = {
            "type": "chat",
            "message": "Hello",
            "conversation_id": "nonexistent_id",
        }
        websocket.send_text(json.dumps(chat_message))

        # Should receive error message
        data = websocket.receive_text()
        error_msg = json.loads(data)
        assert error_msg["type"] == "error"
        assert "Conversation not found" in error_msg["data"]["error"]
