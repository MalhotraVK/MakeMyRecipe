"""Tests for LLM service with Anthropic integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.makemyrecipe.models.chat import ChatMessage
from src.makemyrecipe.services.llm_service import LLMService


class TestLLMServiceAnthropicIntegration:
    """Test cases for LLM service with Anthropic integration."""

    @pytest.fixture
    def llm_service(self):
        """Create an LLMService instance for testing."""
        return LLMService()

    @pytest.fixture
    def recipe_messages(self):
        """Create sample recipe-related messages."""
        return [
            ChatMessage(role="user", content="I want to make a delicious pasta recipe"),
        ]

    @pytest.fixture
    def non_recipe_messages(self):
        """Create sample non-recipe messages."""
        return [
            ChatMessage(role="user", content="What's the weather like today?"),
        ]

    def test_is_recipe_query_positive_cases(self, llm_service):
        """Test recipe query detection for positive cases."""
        recipe_queries = [
            "I want to cook pasta",
            "Give me a recipe for chocolate cake",
            "How do I bake bread?",
            "What ingredients do I need for pizza?",
            "Show me how to make sushi",
            "I need a vegetarian dinner recipe",
            "How to prepare chicken curry?",
            "What's a good dessert recipe?",
            "I want to bake cookies",
            "Help me cook something with tomatoes",
        ]

        for query in recipe_queries:
            messages = [ChatMessage(role="user", content=query)]
            assert llm_service._is_recipe_query(
                messages
            ), f"Should detect recipe query: {query}"

    def test_is_recipe_query_negative_cases(self, llm_service):
        """Test recipe query detection for negative cases."""
        non_recipe_queries = [
            "What's the weather like?",
            "Tell me a joke",
            "How are you doing?",
            "What time is it?",
            "Can you help me with math?",
            "What's the capital of France?",
            "I need help with my homework",
            "How do I fix my computer?",
        ]

        for query in non_recipe_queries:
            messages = [ChatMessage(role="user", content=query)]
            assert not llm_service._is_recipe_query(
                messages
            ), f"Should not detect recipe query: {query}"

    def test_is_recipe_query_empty_messages(self, llm_service):
        """Test recipe query detection with empty messages."""
        assert not llm_service._is_recipe_query([])

    @pytest.mark.asyncio
    @patch("src.makemyrecipe.services.llm_service.settings")
    async def test_generate_response_uses_anthropic_for_recipes(
        self, mock_settings, llm_service, recipe_messages
    ):
        """Test that recipe queries use Anthropic service."""
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_enable_web_search = True

        # Mock the Anthropic service
        mock_anthropic_service = AsyncMock()
        mock_anthropic_service.generate_recipe_response.return_value = (
            "Here's a great pasta recipe with web search results!",
            [
                {
                    "title": "Best Pasta",
                    "url": "https://example.com",
                    "snippet": "Great recipe",
                }
            ],
        )
        llm_service.anthropic_service = mock_anthropic_service

        response = await llm_service.generate_response(recipe_messages)

        assert response == "Here's a great pasta recipe with web search results!"
        mock_anthropic_service.generate_recipe_response.assert_called_once_with(
            recipe_messages, None, use_web_search=True
        )

    @pytest.mark.asyncio
    @patch("src.makemyrecipe.services.llm_service.settings")
    async def test_generate_response_with_citations_for_recipes(
        self, mock_settings, llm_service, recipe_messages
    ):
        """Test that recipe queries return citations."""
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_enable_web_search = True

        # Mock the Anthropic service
        mock_anthropic_service = AsyncMock()
        expected_citations = [
            {
                "title": "Best Pasta Recipe",
                "url": "https://example.com/pasta",
                "snippet": "Delicious pasta",
            },
            {
                "title": "Italian Cooking",
                "url": "https://example.com/italian",
                "snippet": "Authentic recipes",
            },
        ]
        mock_anthropic_service.generate_recipe_response.return_value = (
            "Here's a pasta recipe with sources!",
            expected_citations,
        )
        llm_service.anthropic_service = mock_anthropic_service

        response, citations = await llm_service.generate_response_with_citations(
            recipe_messages
        )

        assert response == "Here's a pasta recipe with sources!"
        assert citations == expected_citations
        mock_anthropic_service.generate_recipe_response.assert_called_once_with(
            recipe_messages, None, use_web_search=True
        )

    @pytest.mark.asyncio
    @patch("src.makemyrecipe.services.llm_service.settings")
    async def test_generate_response_fallback_to_litellm(
        self, mock_settings, llm_service, non_recipe_messages
    ):
        """Test that non-recipe queries fall back to LiteLLM."""
        mock_settings.anthropic_api_key = "test-key"

        # Mock LiteLLM
        with patch(
            "src.makemyrecipe.services.llm_service.litellm_module"
        ) as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Here's the weather information"
            mock_litellm.acompletion = AsyncMock(return_value=mock_response)

            response = await llm_service.generate_response(non_recipe_messages)

            assert response == "Here's the weather information"
            mock_litellm.acompletion.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.makemyrecipe.services.llm_service.settings")
    async def test_anthropic_service_failure_fallback(
        self, mock_settings, llm_service, recipe_messages
    ):
        """Test fallback when Anthropic service fails."""
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_enable_web_search = True

        # Mock Anthropic service to raise an exception
        mock_anthropic_service = AsyncMock()
        mock_anthropic_service.generate_recipe_response.side_effect = Exception(
            "API Error"
        )
        llm_service.anthropic_service = mock_anthropic_service

        # Mock LiteLLM as fallback
        with patch(
            "src.makemyrecipe.services.llm_service.litellm_module"
        ) as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Fallback pasta recipe"
            mock_litellm.acompletion = AsyncMock(return_value=mock_response)

            response = await llm_service.generate_response(recipe_messages)

            assert response == "Fallback pasta recipe"
            mock_litellm.acompletion.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.makemyrecipe.services.llm_service.settings")
    async def test_no_anthropic_api_key_uses_litellm(
        self, mock_settings, llm_service, recipe_messages
    ):
        """Test that LiteLLM is used when no Anthropic API key is provided."""
        mock_settings.anthropic_api_key = None

        # Mock LiteLLM
        with patch(
            "src.makemyrecipe.services.llm_service.litellm_module"
        ) as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "LiteLLM pasta recipe"
            mock_litellm.acompletion = AsyncMock(return_value=mock_response)

            response = await llm_service.generate_response(recipe_messages)

            assert response == "LiteLLM pasta recipe"
            mock_litellm.acompletion.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.makemyrecipe.services.llm_service.settings")
    async def test_web_search_disabled(
        self, mock_settings, llm_service, recipe_messages
    ):
        """Test behavior when web search is disabled."""
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_enable_web_search = False

        # Mock the Anthropic service
        mock_anthropic_service = AsyncMock()
        mock_anthropic_service.generate_recipe_response.return_value = (
            "Recipe without web search",
            [],
        )
        llm_service.anthropic_service = mock_anthropic_service

        response = await llm_service.generate_response(recipe_messages)

        assert response == "Recipe without web search"
        mock_anthropic_service.generate_recipe_response.assert_called_once_with(
            recipe_messages, None, use_web_search=False
        )

    @pytest.mark.asyncio
    async def test_generate_response_with_citations_fallback(
        self, llm_service, non_recipe_messages
    ):
        """Test that non-recipe queries return empty citations."""
        # Mock LiteLLM
        with patch(
            "src.makemyrecipe.services.llm_service.litellm_module"
        ) as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "General response"
            mock_litellm.acompletion = AsyncMock(return_value=mock_response)

            response, citations = await llm_service.generate_response_with_citations(
                non_recipe_messages
            )

            assert response == "General response"
            assert citations == []

    @pytest.mark.asyncio
    async def test_generate_response_no_litellm_fallback_to_mock(
        self, llm_service, recipe_messages
    ):
        """Test fallback when neither Anthropic nor LiteLLM is available."""
        # Ensure no Anthropic API key
        with patch("src.makemyrecipe.services.llm_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = None

            # Mock LiteLLM as None
            with patch("src.makemyrecipe.services.llm_service.litellm_module", None):
                response = await llm_service.generate_response(recipe_messages)

                assert isinstance(response, str)
                assert len(response) > 0
                # Should be a mock response about pasta
                assert "pasta" in response.lower() or "recipe" in response.lower()


@pytest.mark.integration
class TestLLMServiceAnthropicIntegrationE2E:
    """End-to-end integration tests for LLM service with Anthropic."""

    @pytest.mark.asyncio
    async def test_recipe_workflow_integration(self):
        """Test the complete recipe workflow integration."""
        from src.makemyrecipe.services.chat_service import chat_service
        from src.makemyrecipe.services.llm_service import llm_service

        # Create a conversation
        conversation = chat_service.create_conversation("test-user")

        # Add a recipe query
        chat_service.add_message(
            conversation.conversation_id, "user", "I want to make pasta carbonara"
        )

        # Generate response (this will use mock/fallback if no real API key)
        response, citations = await llm_service.generate_response_with_citations(
            conversation.messages
        )

        assert isinstance(response, str)
        assert len(response) > 0
        assert isinstance(citations, list)

        # Add the response to conversation
        chat_service.add_message(conversation.conversation_id, "assistant", response)

        # Verify conversation state
        updated_conversation = chat_service.get_conversation(
            conversation.conversation_id
        )
        assert updated_conversation is not None
        assert len(updated_conversation.messages) == 2
        assert updated_conversation.messages[0].role == "user"
        assert updated_conversation.messages[1].role == "assistant"
