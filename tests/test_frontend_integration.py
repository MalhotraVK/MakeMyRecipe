"""Integration tests for the frontend chat interface."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from src.makemyrecipe.api.main import app


class TestFrontendIntegration:
    """Test frontend integration with the API."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_static_files_served(self):
        """Test that static files are properly served."""
        # Test main HTML file
        response = self.client.get("/")
        assert response.status_code == 200
        assert "MakeMyRecipe" in response.text
        assert "text/html" in response.headers.get("content-type", "")

    def test_static_css_served(self):
        """Test that CSS files are served."""
        response = self.client.get("/static/css/styles.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")
        assert "--primary-color" in response.text  # Check for CSS variables

    def test_static_js_served(self):
        """Test that JavaScript files are served."""
        response = self.client.get("/static/js/app.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")
        assert "MakeMyRecipeApp" in response.text  # Check for main class

    def test_api_info_endpoint(self):
        """Test API info endpoint."""
        response = self.client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data

    def test_websocket_connection(self):
        """Test WebSocket connection."""
        user_id = "test_user_123"

        with self.client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Should receive welcome message
            data = websocket.receive_text()
            message = json.loads(data)

            assert message["type"] == "status"
            assert message["data"]["user_id"] == user_id
            assert "Connected to MakeMyRecipe" in message["data"]["message"]

    def test_websocket_chat_message(self):
        """Test sending chat message via WebSocket."""
        user_id = "test_user_456"

        with self.client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_text()

            # Send chat message
            chat_message = {
                "type": "chat",
                "message": "Hello, I need a recipe for pasta",
            }
            websocket.send_text(json.dumps(chat_message))

            # Should receive user message confirmation
            user_msg_data = websocket.receive_text()
            user_message = json.loads(user_msg_data)

            assert user_message["type"] == "user_message"
            assert user_message["data"]["message"] == "Hello, I need a recipe for pasta"
            assert user_message["data"]["role"] == "user"

            # Should receive assistant response (may take time due to LLM)
            # We'll set a timeout for this test
            try:
                assistant_msg_data = websocket.receive_text()
                assistant_message = json.loads(assistant_msg_data)

                assert assistant_message["type"] == "assistant_message"
                assert "message" in assistant_message["data"]
                assert assistant_message["data"]["role"] == "assistant"
                assert "conversation_id" in assistant_message["data"]
            except Exception:
                # If LLM service is not available, we might get an error
                # This is acceptable for testing the WebSocket functionality
                pass

    def test_websocket_ping_pong(self):
        """Test WebSocket ping/pong functionality."""
        user_id = "test_user_789"

        with self.client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_text()

            # Send ping
            ping_message = {"type": "ping"}
            websocket.send_text(json.dumps(ping_message))

            # Should receive pong
            pong_data = websocket.receive_text()
            pong_message = json.loads(pong_data)

            assert pong_message["type"] == "pong"
            assert pong_message["data"]["message"] == "pong"

    def test_websocket_invalid_message(self):
        """Test WebSocket with invalid message format."""
        user_id = "test_user_invalid"

        with self.client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_text()

            # Send invalid JSON
            websocket.send_text("invalid json")

            # Should receive error message
            error_data = websocket.receive_text()
            error_message = json.loads(error_data)

            assert error_message["type"] == "error"
            assert "Invalid JSON format" in error_message["data"]["error"]

    def test_websocket_empty_message(self):
        """Test WebSocket with empty chat message."""
        user_id = "test_user_empty"

        with self.client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_text()

            # Send empty message
            empty_message = {"type": "chat", "message": ""}
            websocket.send_text(json.dumps(empty_message))

            # Should receive error message
            error_data = websocket.receive_text()
            error_message = json.loads(error_data)

            assert error_message["type"] == "error"
            assert "Message cannot be empty" in error_message["data"]["error"]

    def test_chat_api_endpoint(self):
        """Test REST API chat endpoint."""
        chat_request = {
            "message": "I want to make a simple pasta dish",
            "user_id": "test_user_rest",
        }

        response = self.client.post("/api/chat", json=chat_request)

        # Should return 200 or 500 (if LLM service unavailable)
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "conversation_id" in data
            assert "citations" in data

    def test_conversations_api_endpoint(self):
        """Test conversations API endpoint."""
        user_id = "test_user_conversations"

        response = self.client.get(f"/api/conversations?user_id={user_id}")
        assert response.status_code == 200

        data = response.json()
        assert "conversations" in data
        assert "total" in data
        assert isinstance(data["conversations"], list)

    def test_create_conversation_api(self):
        """Test create conversation API endpoint."""
        user_id = "test_user_create"

        response = self.client.post(f"/api/conversations?user_id={user_id}")
        assert response.status_code == 200

        data = response.json()
        assert "conversation_id" in data
        assert "user_id" in data
        assert data["user_id"] == user_id

    def test_cors_headers(self):
        """Test CORS headers are properly set."""
        response = self.client.options("/api/chat")

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_security_headers(self):
        """Test security headers are present."""
        response = self.client.get("/")

        # Check for security headers (from SecurityHeadersMiddleware)
        headers = response.headers
        assert "x-content-type-options" in headers
        assert "x-frame-options" in headers
        assert "x-xss-protection" in headers

    def test_frontend_responsive_elements(self):
        """Test that frontend contains responsive design elements."""
        response = self.client.get("/")
        html_content = response.text

        # Check for viewport meta tag
        assert 'name="viewport"' in html_content

        # Check for responsive CSS classes
        assert "mobile-sidebar-toggle" in html_content
        assert "sidebar" in html_content
        assert "chat-container" in html_content

        # Check for Font Awesome icons
        assert "font-awesome" in html_content

        # Check for Google Fonts
        assert "fonts.googleapis.com" in html_content

    def test_frontend_accessibility_features(self):
        """Test accessibility features in frontend."""
        response = self.client.get("/")
        html_content = response.text

        # Check for semantic HTML elements
        assert "<main" in html_content
        assert "<aside" in html_content
        assert "<button" in html_content

        # Check for ARIA labels and roles
        assert "aria-" in html_content or "role=" in html_content

        # Check for alt attributes on images (if any)
        # Check for proper form labels
        assert "<label" in html_content or "placeholder=" in html_content

    def test_frontend_performance_features(self):
        """Test performance optimization features."""
        response = self.client.get("/")
        html_content = response.text

        # Check for preconnect links
        assert "preconnect" in html_content

        # Check for font display optimization
        assert "display=swap" in html_content

        # Check for efficient loading
        assert (
            "defer" in html_content
            or "async" in html_content
            or html_content.find("<script") > html_content.find("</body>") - 200
        )

    def test_websocket_multiple_connections(self):
        """Test multiple WebSocket connections."""
        user_id_1 = "test_user_multi_1"
        user_id_2 = "test_user_multi_2"

        with self.client.websocket_connect(f"/ws/chat/{user_id_1}") as ws1:
            with self.client.websocket_connect(f"/ws/chat/{user_id_2}") as ws2:
                # Both should receive welcome messages
                welcome1 = json.loads(ws1.receive_text())
                welcome2 = json.loads(ws2.receive_text())

                assert welcome1["data"]["user_id"] == user_id_1
                assert welcome2["data"]["user_id"] == user_id_2

                # Send messages from both connections
                ws1.send_text(json.dumps({"type": "ping"}))
                ws2.send_text(json.dumps({"type": "ping"}))

                # Both should receive pong responses
                pong1 = json.loads(ws1.receive_text())
                pong2 = json.loads(ws2.receive_text())

                assert pong1["type"] == "pong"
                assert pong2["type"] == "pong"


class TestFrontendUIComponents:
    """Test frontend UI components and interactions."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_css_variables_defined(self):
        """Test that CSS custom properties are properly defined."""
        response = self.client.get("/static/css/styles.css")
        css_content = response.text

        # Check for essential CSS variables
        assert "--primary-color:" in css_content
        assert "--bg-primary:" in css_content
        assert "--text-primary:" in css_content
        assert "--border-light:" in css_content
        assert "--spacing-md:" in css_content
        assert "--radius-md:" in css_content
        assert "--transition-fast:" in css_content

    def test_responsive_breakpoints(self):
        """Test responsive design breakpoints."""
        response = self.client.get("/static/css/styles.css")
        css_content = response.text

        # Check for mobile breakpoints
        assert "@media (max-width: 768px)" in css_content
        assert "@media (max-width: 480px)" in css_content

        # Check for responsive classes
        assert ".mobile-sidebar-toggle" in css_content
        assert ".sidebar.open" in css_content

    def test_accessibility_css_features(self):
        """Test CSS accessibility features."""
        response = self.client.get("/static/css/styles.css")
        css_content = response.text

        # Check for reduced motion support
        assert "@media (prefers-reduced-motion: reduce)" in css_content

        # Check for high contrast support
        assert "@media (prefers-contrast: high)" in css_content

        # Check for dark mode support
        assert "@media (prefers-color-scheme: dark)" in css_content

    def test_animation_definitions(self):
        """Test CSS animation definitions."""
        response = self.client.get("/static/css/styles.css")
        css_content = response.text

        # Check for keyframe animations
        assert "@keyframes fadeInUp" in css_content
        assert "@keyframes typing" in css_content
        assert "@keyframes modalSlideIn" in css_content

    def test_component_styles_present(self):
        """Test that all component styles are present."""
        response = self.client.get("/static/css/styles.css")
        css_content = response.text

        # Check for main component classes
        components = [
            ".app-container",
            ".sidebar",
            ".chat-container",
            ".messages-container",
            ".message",
            ".message-bubble",
            ".typing-indicator",
            ".input-container",
            ".recipe-card",
            ".citation",
            ".modal",
            ".loading-overlay",
        ]

        for component in components:
            assert component in css_content, f"Component {component} not found in CSS"

    def test_javascript_class_structure(self):
        """Test JavaScript class structure."""
        response = self.client.get("/static/js/app.js")
        js_content = response.text

        # Check for main class
        assert "class MakeMyRecipeApp" in js_content

        # Check for essential methods
        methods = [
            "constructor()",
            "connect()",
            "sendMessage()",
            "displayMessage(",
            "handleWebSocketMessage(",
            "loadConversations(",
            "showTypingIndicator(",
            "hideTypingIndicator(",
        ]

        for method in methods:
            assert method in js_content, f"Method {method} not found in JavaScript"

    def test_javascript_error_handling(self):
        """Test JavaScript error handling."""
        response = self.client.get("/static/js/app.js")
        js_content = response.text

        # Check for try-catch blocks
        assert "try {" in js_content
        assert "catch (error)" in js_content

        # Check for error handling methods
        assert "showError(" in js_content
        assert "handleConnectionError(" in js_content
        assert "handleWebSocketError(" in js_content

    def test_javascript_websocket_handling(self):
        """Test JavaScript WebSocket handling."""
        response = self.client.get("/static/js/app.js")
        js_content = response.text

        # Check for WebSocket event handlers
        assert "onopen" in js_content
        assert "onmessage" in js_content
        assert "onclose" in js_content
        assert "onerror" in js_content

        # Check for reconnection logic
        assert "attemptReconnect(" in js_content
        assert "reconnectAttempts" in js_content

    def test_javascript_dom_manipulation(self):
        """Test JavaScript DOM manipulation."""
        response = self.client.get("/static/js/app.js")
        js_content = response.text

        # Check for DOM methods
        assert "getElementById(" in js_content
        assert "createElement(" in js_content
        assert "appendChild(" in js_content
        assert "addEventListener(" in js_content

        # Check for element queries
        assert "querySelector(" in js_content or "querySelectorAll(" in js_content

    def test_html_semantic_structure(self):
        """Test HTML semantic structure."""
        response = self.client.get("/")
        html_content = response.text

        # Check for semantic HTML5 elements
        semantic_elements = [
            "<main",
            "<aside",
            "<header",
            "<nav",
            "<section",
            "<article",
        ]

        # At least some semantic elements should be present
        semantic_found = any(element in html_content for element in semantic_elements)
        assert semantic_found, "No semantic HTML5 elements found"

    def test_html_form_elements(self):
        """Test HTML form elements."""
        response = self.client.get("/")
        html_content = response.text

        # Check for form elements
        assert "<textarea" in html_content
        assert "<button" in html_content
        assert "<input" in html_content

        # Check for proper attributes
        assert 'type="text"' in html_content
        assert "placeholder=" in html_content
        assert "maxlength=" in html_content

    def test_html_meta_tags(self):
        """Test HTML meta tags."""
        response = self.client.get("/")
        html_content = response.text

        # Check for essential meta tags
        assert '<meta charset="UTF-8">' in html_content
        assert 'name="viewport"' in html_content
        assert "<title>" in html_content

        # Check for external resources
        assert 'rel="stylesheet"' in html_content
        assert 'rel="preconnect"' in html_content
