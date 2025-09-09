"""Tests for search tag functionality in AnthropicService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.makemyrecipe.models.chat import ChatMessage
from src.makemyrecipe.services.anthropic_service import AnthropicService


class TestSearchTagFunctionality:
    """Test cases for search tag detection and processing."""

    @pytest.fixture
    def anthropic_service(self):
        """Create an AnthropicService instance for testing."""
        return AnthropicService()

    def test_extract_search_queries_single_tag(self, anthropic_service):
        """Test extracting a single search query from text."""
        text = "I need to find a recipe. <search>pasta carbonara recipe</search> Let me help you with that."
        
        queries = anthropic_service._extract_search_queries(text)
        
        assert len(queries) == 1
        assert queries[0] == "pasta carbonara recipe"

    def test_extract_search_queries_multiple_tags(self, anthropic_service):
        """Test extracting multiple search queries from text."""
        text = """
        Let me search for some recipes:
        <search>italian pasta recipes</search>
        And also:
        <search>vegetarian pasta dishes</search>
        """
        
        queries = anthropic_service._extract_search_queries(text)
        
        assert len(queries) == 2
        assert "italian pasta recipes" in queries
        assert "vegetarian pasta dishes" in queries

    def test_extract_search_queries_no_tags(self, anthropic_service):
        """Test extracting search queries when no tags are present."""
        text = "This is just regular text without any search tags."
        
        queries = anthropic_service._extract_search_queries(text)
        
        assert len(queries) == 0

    def test_extract_search_queries_empty_tags(self, anthropic_service):
        """Test extracting search queries with empty tags."""
        text = "Here's an empty search: <search></search> and another <search>   </search>"
        
        queries = anthropic_service._extract_search_queries(text)
        
        assert len(queries) == 0

    def test_extract_search_queries_multiline(self, anthropic_service):
        """Test extracting search queries that span multiple lines."""
        text = """
        <search>
        chicken breast recipes
        with herbs and spices
        </search>
        """
        
        queries = anthropic_service._extract_search_queries(text)
        
        assert len(queries) == 1
        assert "chicken breast recipes\n        with herbs and spices" in queries[0]

    def test_extract_search_queries_case_insensitive(self, anthropic_service):
        """Test that search tag extraction is case insensitive."""
        text = "Let me <SEARCH>uppercase search</SEARCH> and <Search>mixed case</Search>"
        
        queries = anthropic_service._extract_search_queries(text)
        
        assert len(queries) == 2
        assert "uppercase search" in queries
        assert "mixed case" in queries

    def test_remove_search_tags_single_tag(self, anthropic_service):
        """Test removing a single search tag from text."""
        text = "I need to find a recipe. <search>pasta carbonara recipe</search> Let me help you with that."
        
        cleaned_text = anthropic_service._remove_search_tags(text)
        
        assert "<search>" not in cleaned_text
        assert "</search>" not in cleaned_text
        assert "pasta carbonara recipe" not in cleaned_text
        assert "I need to find a recipe." in cleaned_text
        assert "Let me help you with that." in cleaned_text

    def test_remove_search_tags_multiple_tags(self, anthropic_service):
        """Test removing multiple search tags from text."""
        text = """
        Let me search for recipes:
        <search>italian pasta recipes</search>
        And also:
        <search>vegetarian pasta dishes</search>
        Here are the results.
        """
        
        cleaned_text = anthropic_service._remove_search_tags(text)
        
        assert "<search>" not in cleaned_text
        assert "</search>" not in cleaned_text
        assert "italian pasta recipes" not in cleaned_text
        assert "vegetarian pasta dishes" not in cleaned_text
        assert "Let me search for recipes:" in cleaned_text
        assert "And also:" in cleaned_text
        assert "Here are the results." in cleaned_text

    def test_remove_search_tags_no_tags(self, anthropic_service):
        """Test removing search tags when no tags are present."""
        text = "This is just regular text without any search tags."
        
        cleaned_text = anthropic_service._remove_search_tags(text)
        
        assert cleaned_text == text

    def test_remove_search_tags_case_insensitive(self, anthropic_service):
        """Test that search tag removal is case insensitive."""
        text = "Let me <SEARCH>uppercase search</SEARCH> and <Search>mixed case</Search>"
        
        cleaned_text = anthropic_service._remove_search_tags(text)
        
        assert "<SEARCH>" not in cleaned_text
        assert "<Search>" not in cleaned_text
        assert "uppercase search" not in cleaned_text
        assert "mixed case" not in cleaned_text

    @pytest.mark.asyncio
    async def test_perform_search_success(self, anthropic_service):
        """Test successful search execution."""
        # Mock the client and response
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "Here are some great pasta recipes..."
        mock_response.content = [mock_text_block]
        
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response
        anthropic_service.client = mock_client
        
        with patch("src.makemyrecipe.services.anthropic_service.settings") as mock_settings:
            mock_settings.anthropic_model = "claude-sonnet-4-20250514"
            mock_settings.anthropic_max_tokens = 2000
            mock_settings.anthropic_temperature = 0.7
            
            content, citations = await anthropic_service._perform_search("pasta recipes")
            
            assert isinstance(content, str)
            assert "pasta recipes" in content.lower()
            assert isinstance(citations, list)
            
            # Verify the client was called correctly
            mock_client.messages.create.assert_called_once()
            call_args = mock_client.messages.create.call_args
            assert call_args[1]["temperature"] == 0.1  # Lower temperature for search
            assert "tools" in call_args[1]

    @pytest.mark.asyncio
    async def test_perform_search_no_client(self, anthropic_service):
        """Test search when client is not available."""
        anthropic_service.client = None
        
        content, citations = await anthropic_service._perform_search("pasta recipes")
        
        assert content == ""
        assert citations == []

    @pytest.mark.asyncio
    async def test_perform_search_error(self, anthropic_service):
        """Test search when an error occurs."""
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        anthropic_service.client = mock_client
        
        content, citations = await anthropic_service._perform_search("pasta recipes")
        
        assert "Search error:" in content
        assert "API Error" in content
        assert citations == []

    def test_create_recipe_system_prompt_includes_search_instructions(self, anthropic_service):
        """Test that the system prompt includes search tag instructions."""
        prompt = anthropic_service._create_recipe_system_prompt()
        
        assert "search tags" in prompt.lower()
        assert "<search>" in prompt
        assert "</search>" in prompt
        assert "search query here" in prompt
        assert "examples of when to use search tags" in prompt.lower()

    @pytest.mark.asyncio
    @patch("src.makemyrecipe.services.anthropic_service.settings")
    async def test_generate_recipe_response_with_search_tags(self, mock_settings, anthropic_service):
        """Test recipe response generation with search tags."""
        # Setup mock settings
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.anthropic_max_tokens = 2000
        mock_settings.anthropic_temperature = 0.7
        
        # Mock initial response with search tags
        mock_initial_response = MagicMock()
        mock_initial_text = MagicMock()
        mock_initial_text.text = "I'll help you find a recipe. <search>pasta carbonara recipe</search> Let me search for that."
        mock_initial_response.content = [mock_initial_text]
        
        # Mock search response
        mock_search_response = MagicMock()
        mock_search_text = MagicMock()
        mock_search_text.text = "Found great carbonara recipes from Allrecipes and Food Network."
        mock_search_response.content = [mock_search_text]
        
        # Mock final response
        mock_final_response = MagicMock()
        mock_final_text = MagicMock()
        mock_final_text.text = "Here's a great carbonara recipe based on my search results..."
        mock_final_response.content = [mock_final_text]
        
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = [
            mock_initial_response,  # Initial response with search tags
            mock_search_response,   # Search results
            mock_final_response     # Final response with search results
        ]
        anthropic_service.client = mock_client
        
        messages = [ChatMessage(role="user", content="I want to make carbonara")]
        
        content, citations = await anthropic_service.generate_recipe_response(messages)
        
        assert isinstance(content, str)
        assert "carbonara recipe" in content.lower()
        assert isinstance(citations, list)
        
        # Verify multiple API calls were made
        assert mock_client.messages.create.call_count == 3

    @pytest.mark.asyncio
    @patch("src.makemyrecipe.services.anthropic_service.settings")
    async def test_generate_recipe_response_no_search_tags(self, mock_settings, anthropic_service):
        """Test recipe response generation without search tags."""
        # Setup mock settings
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.anthropic_max_tokens = 2000
        mock_settings.anthropic_temperature = 0.7
        
        # Mock response without search tags
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "Here's a basic carbonara recipe from my knowledge..."
        mock_response.content = [mock_text_block]
        
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response
        anthropic_service.client = mock_client
        
        messages = [ChatMessage(role="user", content="Tell me about carbonara")]
        
        content, citations = await anthropic_service.generate_recipe_response(messages)
        
        assert isinstance(content, str)
        assert "carbonara recipe" in content.lower()
        assert isinstance(citations, list)
        assert len(citations) == 0  # No search performed, so no citations
        
        # Verify only one API call was made
        assert mock_client.messages.create.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_recipe_response_search_disabled(self, anthropic_service):
        """Test recipe response generation with search disabled."""
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "I'll help with recipes. <search>pasta recipes</search> Here's what I know..."
        mock_response.content = [mock_text_block]
        
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response
        anthropic_service.client = mock_client
        
        messages = [ChatMessage(role="user", content="I want pasta recipes")]
        
        # Disable web search
        content, citations = await anthropic_service.generate_recipe_response(
            messages, use_web_search=False
        )
        
        assert isinstance(content, str)
        assert isinstance(citations, list)
        assert len(citations) == 0  # No search performed
        
        # Verify only one API call was made (no search execution)
        assert mock_client.messages.create.call_count == 1