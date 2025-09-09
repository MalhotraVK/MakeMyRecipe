"""Tests for Anthropic service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.makemyrecipe.models.chat import ChatMessage
from src.makemyrecipe.services.anthropic_service import AnthropicService, RateLimiter


class TestAnthropicService:
    """Test cases for AnthropicService."""

    @pytest.fixture
    def anthropic_service(self):
        """Create an AnthropicService instance for testing."""
        return AnthropicService()

    @pytest.fixture
    def sample_messages(self):
        """Create sample chat messages for testing."""
        return [
            ChatMessage(role="user", content="I want to make pasta"),
            ChatMessage(role="assistant", content="What kind of pasta would you like?"),
            ChatMessage(role="user", content="Something with tomatoes and basil"),
        ]

    def test_init(self, anthropic_service):
        """Test AnthropicService initialization."""
        assert anthropic_service._rate_limiter is not None
        assert isinstance(anthropic_service._rate_limiter, RateLimiter)

    def test_get_web_search_tool(self, anthropic_service):
        """Test web search tool configuration."""
        tool = anthropic_service._get_web_search_tool()

        assert tool["type"] == "web_search_20250305"
        assert tool["name"] == "web_search"
        # Web search tool doesn't accept custom description field
        assert "description" not in tool

    def test_web_search_tool_format_is_valid(self, anthropic_service):
        """Test that web search tool format matches Anthropic API requirements."""
        from anthropic.types.web_search_tool_20250305_param import (
            WebSearchTool20250305Param,
        )

        tool = anthropic_service._get_web_search_tool()

        # Verify the tool matches the expected format
        # This should not raise any validation errors
        try:
            # The tool should be a valid WebSearchTool20250305Param
            assert isinstance(tool, dict)
            assert tool.get("type") == "web_search_20250305"
            assert tool.get("name") == "web_search"

            # Verify no extra fields that would cause 400 error
            allowed_fields = {
                "type",
                "name",
                "allowed_domains",
                "blocked_domains",
                "cache_control",
                "max_uses",
                "user_location",
            }
            tool_fields = set(tool.keys())
            extra_fields = tool_fields - allowed_fields
            assert (
                not extra_fields
            ), f"Tool has extra fields not allowed by API: {extra_fields}"

        except Exception as e:
            pytest.fail(f"Web search tool format is invalid: {e}")

    def test_create_recipe_system_prompt(self, anthropic_service):
        """Test recipe system prompt creation."""
        prompt = anthropic_service._create_recipe_system_prompt()

        assert "MakeMyRecipe" in prompt
        assert "recipe" in prompt.lower()
        assert "cooking" in prompt.lower()
        assert "search tags" in prompt.lower()
        assert "<search>" in prompt
        assert "</search>" in prompt

    def test_convert_messages(self, anthropic_service, sample_messages):
        """Test message conversion to Anthropic format."""
        claude_messages = anthropic_service._convert_messages(sample_messages)

        assert len(claude_messages) == 3
        assert claude_messages[0]["role"] == "user"
        assert claude_messages[0]["content"] == "I want to make pasta"
        assert claude_messages[1]["role"] == "assistant"
        assert claude_messages[2]["role"] == "user"

    def test_convert_messages_filters_system_messages(self, anthropic_service):
        """Test that system messages are filtered out during conversion."""
        messages = [
            ChatMessage(role="system", content="You are a helpful assistant"),
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!"),
        ]

        claude_messages = anthropic_service._convert_messages(messages)

        # System messages should be filtered out
        assert len(claude_messages) == 2
        assert all(msg["role"] in ["user", "assistant"] for msg in claude_messages)

    @patch("src.makemyrecipe.services.anthropic_service.settings")
    def test_setup_client_no_api_key(self, mock_settings, anthropic_service):
        """Test client setup when no API key is provided."""
        mock_settings.anthropic_api_key = None

        anthropic_service._setup_client()

        assert anthropic_service.client is None
        assert anthropic_service.sync_client is None

    @patch("src.makemyrecipe.services.anthropic_service.settings")
    @patch("src.makemyrecipe.services.anthropic_service.AsyncAnthropic")
    @patch("src.makemyrecipe.services.anthropic_service.Anthropic")
    def test_setup_client_with_api_key(
        self, mock_anthropic, mock_async_anthropic, mock_settings
    ):
        """Test client setup with API key."""
        mock_settings.anthropic_api_key = "test-key"
        mock_async_client = AsyncMock()
        mock_sync_client = MagicMock()
        mock_async_anthropic.return_value = mock_async_client
        mock_anthropic.return_value = mock_sync_client

        service = AnthropicService()

        mock_async_anthropic.assert_called_once_with(api_key="test-key")
        mock_anthropic.assert_called_once_with(api_key="test-key")
        assert service.client == mock_async_client
        assert service.sync_client == mock_sync_client

    def test_get_fallback_response_empty_messages(self, anthropic_service):
        """Test fallback response with empty messages."""
        response = anthropic_service._get_fallback_response([])

        assert "MakeMyRecipe" in response
        assert "cooking assistant" in response.lower()

    def test_get_fallback_response_recipe_query(self, anthropic_service):
        """Test fallback response for recipe queries."""
        messages = [ChatMessage(role="user", content="I need a recipe for pasta")]

        response = anthropic_service._get_fallback_response(messages)

        assert "recipe" in response.lower()
        assert "ingredients" in response.lower()

    @pytest.mark.asyncio
    async def test_generate_recipe_response_no_client(
        self, anthropic_service, sample_messages
    ):
        """Test recipe response generation when client is not available."""
        anthropic_service.client = None

        response, citations = await anthropic_service.generate_recipe_response(
            sample_messages
        )

        assert isinstance(response, str)
        assert isinstance(citations, list)
        assert len(citations) == 0

    @pytest.mark.asyncio
    @patch("src.makemyrecipe.services.anthropic_service.settings")
    async def test_generate_recipe_response_with_mock_client(
        self, mock_settings, sample_messages
    ):
        """Test recipe response generation with mocked client."""
        # Setup mock settings
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.anthropic_max_tokens = 2000
        mock_settings.anthropic_temperature = 0.7
        mock_settings.anthropic_rate_limit_rpm = 50

        # Create mock response
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "Here's a great pasta recipe with tomatoes and basil!"
        mock_response.content = [mock_text_block]

        # Create mock client
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        # Create service and set mock client
        service = AnthropicService()
        service.client = mock_client

        response, citations = await service.generate_recipe_response(sample_messages)

        assert isinstance(response, str)
        assert "pasta recipe" in response.lower()
        assert isinstance(citations, list)

        # Verify client was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["model"] == "claude-sonnet-4-20250514"
        assert call_args[1]["max_tokens"] == 2000
        assert call_args[1]["temperature"] == 0.7
        assert "tools" in call_args[1]

    def test_extract_response_content_text_only(self, anthropic_service):
        """Test extracting content from response with text only."""
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "This is a recipe response"
        mock_response.content = [mock_text_block]

        content, citations = anthropic_service._extract_response_content(mock_response)

        assert content == "This is a recipe response"
        assert citations == []

    def test_extract_response_content_with_citations(self, anthropic_service):
        """Test extracting content with citations."""
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "Here's a recipe"

        # Mock tool use block with search results
        from anthropic.types import ToolUseBlock

        mock_tool_block = MagicMock(spec=ToolUseBlock)
        mock_tool_block.input = {
            "results": [
                {
                    "title": "Best Pasta Recipe",
                    "url": "https://example.com/pasta",
                    "snippet": "A delicious pasta recipe...",
                }
            ]
        }

        mock_response.content = [mock_text_block, mock_tool_block]

        content, citations = anthropic_service._extract_response_content(mock_response)

        assert "Here's a recipe" in content
        assert "**Sources:**" in content
        assert len(citations) == 1
        assert citations[0]["title"] == "Best Pasta Recipe"
        assert citations[0]["url"] == "https://example.com/pasta"


class TestRateLimiter:
    """Test cases for RateLimiter."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a RateLimiter instance for testing."""
        return RateLimiter(max_requests_per_minute=5)

    @pytest.mark.asyncio
    async def test_rate_limiter_under_limit(self, rate_limiter):
        """Test rate limiter when under the limit."""
        # Should not wait when under limit
        await rate_limiter.wait_if_needed()
        rate_limiter.update_usage()

        # Should still not wait
        await rate_limiter.wait_if_needed()
        rate_limiter.update_usage()

        assert len(rate_limiter.requests) == 2

    @pytest.mark.asyncio
    async def test_rate_limiter_at_limit(self, rate_limiter):
        """Test rate limiter when at the limit."""
        # Mock time.time and asyncio.sleep to control timing
        with patch("time.time") as mock_time, patch("asyncio.sleep") as mock_sleep:
            # Set up initial time
            mock_time.return_value = 100.0
            mock_sleep.return_value = None  # Mock async sleep

            # Fill up to the limit
            for _ in range(5):
                await rate_limiter.wait_if_needed()
                rate_limiter.update_usage()

            assert len(rate_limiter.requests) == 5

            # Now simulate time passing (more than 60 seconds)
            # This should clean up old requests when we call wait_if_needed again
            mock_time.return_value = 170.0  # 70 seconds later

            # This should clean up old requests since they're now older than 60 seconds
            await rate_limiter.wait_if_needed()

            # Requests should be cleaned up
            assert len(rate_limiter.requests) == 0

    def test_update_usage(self, rate_limiter):
        """Test usage tracking update."""
        initial_count = len(rate_limiter.requests)

        rate_limiter.update_usage()

        assert len(rate_limiter.requests) == initial_count + 1
        assert rate_limiter.requests[-1] > 0  # Should be a timestamp


@pytest.mark.integration
class TestAnthropicServiceIntegration:
    """Integration tests for AnthropicService."""

    @pytest.mark.asyncio
    async def test_recipe_query_detection(self):
        """Test that recipe queries are properly detected."""
        from src.makemyrecipe.services.llm_service import LLMService

        llm_service = LLMService()

        # Test recipe-related queries
        recipe_messages = [
            [ChatMessage(role="user", content="I want to cook pasta")],
            [ChatMessage(role="user", content="Give me a recipe for chocolate cake")],
            [ChatMessage(role="user", content="How do I bake bread?")],
            [ChatMessage(role="user", content="What ingredients do I need for pizza?")],
        ]

        for messages in recipe_messages:
            assert llm_service._is_recipe_query(
                messages
            ), f"Should detect recipe query: {messages[0].content}"

        # Test non-recipe queries
        non_recipe_messages = [
            [ChatMessage(role="user", content="What's the weather like?")],
            [ChatMessage(role="user", content="Tell me a joke")],
            [ChatMessage(role="user", content="How are you doing?")],
        ]

        for messages in non_recipe_messages:
            assert not llm_service._is_recipe_query(
                messages
            ), f"Should not detect recipe query: {messages[0].content}"
