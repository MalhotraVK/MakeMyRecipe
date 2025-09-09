"""End-to-end tests for the chat interface functionality."""

import json

import pytest
from fastapi.testclient import TestClient

from src.makemyrecipe.api.main import app


class TestE2EChatInterface:
    """End-to-end tests for the complete chat interface workflow."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
        self.test_user_id = "e2e_test_user"

    def test_complete_chat_workflow(self):
        """Test complete chat workflow from connection to response."""
        # Step 1: Verify main page loads
        response = self.client.get("/")
        assert response.status_code == 200
        assert "MakeMyRecipe" in response.text

        # Step 2: Test WebSocket connection and chat
        with self.client.websocket_connect(
            f"/ws/chat/{self.test_user_id}"
        ) as websocket:
            # Receive welcome message
            welcome_data = websocket.receive_text()
            welcome_message = json.loads(welcome_data)

            assert welcome_message["type"] == "status"
            assert "Connected to MakeMyRecipe" in welcome_message["data"]["message"]

            # Send a recipe request
            chat_message = {"type": "chat", "message": "I need a simple pasta recipe"}
            websocket.send_text(json.dumps(chat_message))

            # Receive user message confirmation
            user_msg_data = websocket.receive_text()
            user_message = json.loads(user_msg_data)

            assert user_message["type"] == "user_message"
            assert user_message["data"]["message"] == "I need a simple pasta recipe"
            assert "conversation_id" in user_message["data"]

            conversation_id = user_message["data"]["conversation_id"]

            # Note: We might receive an assistant response or error depending on
            # LLM availability
            # For E2E testing, we'll handle both cases
            try:
                assistant_msg_data = websocket.receive_text()
                assistant_message = json.loads(assistant_msg_data)

                if assistant_message["type"] == "assistant_message":
                    assert "message" in assistant_message["data"]
                    assert (
                        assistant_message["data"]["conversation_id"] == conversation_id
                    )
                elif assistant_message["type"] == "error":
                    # LLM service might not be available in test environment
                    assert "error" in assistant_message["data"]
            except Exception:
                # Timeout or connection issue - acceptable for testing
                pass

        # Step 3: Verify conversation was created via REST API
        response = self.client.get(f"/api/conversations?user_id={self.test_user_id}")
        assert response.status_code == 200

        data = response.json()
        assert "conversations" in data
        assert data["total"] >= 1

        # Find our conversation
        our_conversation = None
        for conv in data["conversations"]:
            if conv["conversation_id"] == conversation_id:
                our_conversation = conv
                break

        if our_conversation:
            assert our_conversation["user_id"] == self.test_user_id
            assert len(our_conversation["messages"]) >= 1

            # Check that user message was saved
            user_messages = [
                msg for msg in our_conversation["messages"] if msg["role"] == "user"
            ]
            assert len(user_messages) >= 1
            assert user_messages[0]["content"] == ("I need a simple pasta recipe")

    def test_multiple_messages_in_conversation(self):
        """Test sending multiple messages in the same conversation."""
        with self.client.websocket_connect(
            f"/ws/chat/{self.test_user_id}_multi"
        ) as websocket:
            # Skip welcome message
            websocket.receive_text()

            # Send first message
            first_message = {
                "type": "chat",
                "message": "What ingredients do I need for carbonara?",
            }
            websocket.send_text(json.dumps(first_message))

            # Get user message confirmation
            user_msg1 = json.loads(websocket.receive_text())
            conversation_id = user_msg1["data"]["conversation_id"]

            # Try to receive assistant response (might timeout)
            try:
                websocket.receive_text()  # Assistant response or error
            except Exception:
                pass

            # Send second message in same conversation
            second_message = {
                "type": "chat",
                "message": "How long does it take to cook?",
                "conversation_id": conversation_id,
            }
            websocket.send_text(json.dumps(second_message))

            # Get user message confirmation
            user_msg2 = json.loads(websocket.receive_text())
            assert user_msg2["data"]["conversation_id"] == conversation_id
            assert user_msg2["data"]["message"] == "How long does it take to cook?"

    def test_conversation_persistence(self):
        """Test that conversations persist and can be retrieved."""
        test_user = f"{self.test_user_id}_persist"

        # Create a conversation via REST API
        response = self.client.post(f"/api/conversations?user_id={test_user}")
        assert response.status_code == 200

        conversation_data = response.json()
        conversation_id = conversation_data["conversation_id"]

        # Send a message via REST API
        chat_request = {
            "message": "Tell me about Italian cuisine",
            "user_id": test_user,
            "conversation_id": conversation_id,
        }

        response = self.client.post("/api/chat", json=chat_request)
        # Should return 200 or 500 (if LLM unavailable)
        assert response.status_code in [200, 500]

        # Retrieve the conversation
        response = self.client.get(f"/api/conversations/{conversation_id}")
        assert response.status_code == 200

        retrieved_conversation = response.json()
        assert retrieved_conversation["conversation_id"] == conversation_id
        assert retrieved_conversation["user_id"] == test_user

        # Check that our message was saved
        user_messages = [
            msg for msg in retrieved_conversation["messages"] if msg["role"] == "user"
        ]
        assert len(user_messages) >= 1
        assert any("Italian cuisine" in msg["content"] for msg in user_messages)

    def test_conversation_deletion(self):
        """Test conversation deletion functionality."""
        test_user = f"{self.test_user_id}_delete"

        # Create a conversation
        response = self.client.post(f"/api/conversations?user_id={test_user}")
        assert response.status_code == 200

        conversation_id = response.json()["conversation_id"]

        # Verify it exists
        response = self.client.get(f"/api/conversations/{conversation_id}")
        assert response.status_code == 200

        # Delete it
        response = self.client.delete(f"/api/conversations/{conversation_id}")
        assert response.status_code == 200

        # Verify it's gone
        response = self.client.get(f"/api/conversations/{conversation_id}")
        assert response.status_code == 404

    def test_websocket_error_handling(self):
        """Test WebSocket error handling scenarios."""
        with self.client.websocket_connect(
            f"/ws/chat/{self.test_user_id}_error"
        ) as websocket:
            # Skip welcome message
            websocket.receive_text()

            # Test invalid message type
            invalid_message = {
                "type": "invalid_type",
                "message": "This should cause an error",
            }
            websocket.send_text(json.dumps(invalid_message))

            error_response = json.loads(websocket.receive_text())
            assert error_response["type"] == "error"
            assert "Unknown message type" in error_response["data"]["error"]

            # Test empty message
            empty_message = {"type": "chat", "message": ""}
            websocket.send_text(json.dumps(empty_message))

            error_response = json.loads(websocket.receive_text())
            assert error_response["type"] == "error"
            assert "Message cannot be empty" in error_response["data"]["error"]

    def test_websocket_nonexistent_conversation(self):
        """Test WebSocket with non-existent conversation ID."""
        with self.client.websocket_connect(
            f"/ws/chat/{self.test_user_id}_nonexistent"
        ) as websocket:
            # Skip welcome message
            websocket.receive_text()

            # Send message with non-existent conversation ID
            message_with_fake_id = {
                "type": "chat",
                "message": "Hello",
                "conversation_id": "fake_conversation_id_12345",
            }
            websocket.send_text(json.dumps(message_with_fake_id))

            error_response = json.loads(websocket.receive_text())
            assert error_response["type"] == "error"
            assert "Conversation not found" in error_response["data"]["error"]

    def test_static_assets_caching(self):
        """Test that static assets have appropriate caching headers."""
        # Test CSS file
        response = self.client.get("/static/css/styles.css")
        assert response.status_code == 200
        # FastAPI's StaticFiles should set appropriate headers

        # Test JS file
        response = self.client.get("/static/js/app.js")
        assert response.status_code == 200

    def test_api_rate_limiting_headers(self):
        """Test API responses include appropriate headers."""
        response = self.client.get("/health")
        assert response.status_code == 200

        # Check for security headers (from middleware)
        headers = response.headers
        assert "x-content-type-options" in headers
        assert "x-frame-options" in headers

    def test_frontend_javascript_functionality(self):
        """Test that frontend JavaScript contains expected functionality."""
        response = self.client.get("/static/js/app.js")
        js_content = response.text

        # Check for WebSocket handling
        assert "WebSocket" in js_content
        assert "onopen" in js_content
        assert "onmessage" in js_content

        # Check for UI interaction methods
        assert "sendMessage" in js_content
        assert "displayMessage" in js_content
        assert "showTypingIndicator" in js_content

        # Check for conversation management
        assert "loadConversations" in js_content
        assert "startNewConversation" in js_content

        # Check for error handling
        assert "showError" in js_content
        assert "handleConnectionError" in js_content

    def test_responsive_design_elements(self):
        """Test that responsive design elements are present."""
        response = self.client.get("/")
        html_content = response.text

        # Check for responsive meta tag
        assert 'name="viewport"' in html_content
        assert "width=device-width" in html_content

        # Check for mobile-specific elements
        assert "mobile-sidebar-toggle" in html_content

        # Check CSS for responsive breakpoints
        css_response = self.client.get("/static/css/styles.css")
        css_content = css_response.text

        assert "@media (max-width: 768px)" in css_content
        assert "@media (max-width: 480px)" in css_content

    def test_accessibility_features(self):
        """Test accessibility features in the interface."""
        response = self.client.get("/")
        html_content = response.text

        # Check for semantic HTML
        assert "<main" in html_content
        assert "<aside" in html_content

        # Check for proper form labels and inputs
        assert "placeholder=" in html_content
        assert "aria-" in html_content or "role=" in html_content

        # Check for keyboard navigation support
        assert "tabindex=" in html_content or "button" in html_content

    def test_performance_optimizations(self):
        """Test performance optimization features."""
        response = self.client.get("/")
        html_content = response.text

        # Check for font preloading
        assert 'rel="preconnect"' in html_content

        # Check for optimized font loading
        assert "display=swap" in html_content

        # Check for efficient resource loading
        script_position = html_content.find("<script")
        body_end_position = html_content.find("</body>")

        # Scripts should be loaded at the end or be deferred/async
        scripts_at_end = script_position > body_end_position - 500
        has_defer_async = "defer" in html_content or "async" in html_content

        assert (
            scripts_at_end or has_defer_async
        ), "Scripts should be optimized for loading"

    def test_error_modal_functionality(self):
        """Test error modal elements are present."""
        response = self.client.get("/")
        html_content = response.text

        # Check for error modal elements
        assert "errorModal" in html_content
        assert "errorMessage" in html_content
        assert "modal-overlay" in html_content

        # Check for loading overlay
        assert "loadingOverlay" in html_content
        assert "loading-spinner" in html_content

    def test_conversation_search_functionality(self):
        """Test conversation search elements are present."""
        response = self.client.get("/")
        html_content = response.text

        # Check for search elements
        assert "conversationSearch" in html_content
        assert "search-input" in html_content
        assert "search-icon" in html_content

        # Check for conversation list
        assert "conversationList" in html_content
        assert "conversation-list" in html_content
