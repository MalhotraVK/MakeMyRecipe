"""End-to-end integration tests for enhanced recipe search functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.makemyrecipe.models.recipe import Citation, Recipe
from src.makemyrecipe.services.anthropic_service import AnthropicService
from src.makemyrecipe.services.recipe_service import RecipeService


class TestE2EEnhancedRecipeSearch:
    """End-to-end tests for the complete enhanced recipe search workflow."""

    @pytest.mark.asyncio
    async def test_complete_search_workflow_with_search_tags(self):
        """Test the complete workflow from user query to Recipe objects with citations."""

        # Mock the Anthropic client responses
        # First response: LLM generates search tags
        mock_initial_response = MagicMock()
        mock_initial_text = MagicMock()
        mock_initial_text.text = """
        I'll help you find a great carbonara recipe! Let me search for authentic recipes.

        <search>authentic Italian carbonara recipe traditional</search>

        I'll look for the best carbonara recipes from trusted cooking sources.
        """
        mock_initial_response.content = [mock_initial_text]

        # Search response: Mock search results
        mock_search_response = MagicMock()
        mock_search_text = MagicMock()
        mock_search_text.text = (
            "Found great carbonara recipes from Allrecipes and Food Network"
        )
        mock_search_response.content = [mock_search_text]

        # Final response: LLM provides structured recipe based on search results
        mock_final_response = MagicMock()
        mock_final_text = MagicMock()
        mock_final_text.text = """
        **Authentic Spaghetti Carbonara**

        This classic Roman pasta dish is creamy, rich, and absolutely delicious. Made with just a few simple ingredients, it's a perfect example of Italian cuisine at its finest.

        **Ingredients:**
        - 400g spaghetti
        - 200g guanciale or pancetta, diced
        - 4 large eggs
        - 100g Pecorino Romano cheese, grated
        - Freshly ground black pepper
        - Salt for pasta water

        **Instructions:**
        1. Bring a large pot of salted water to boil and cook spaghetti until al dente
        2. While pasta cooks, heat a large skillet and cook guanciale until crispy
        3. In a bowl, whisk together eggs, grated cheese, and black pepper
        4. Drain pasta, reserving 1 cup of pasta water
        5. Add hot pasta to the skillet with guanciale
        6. Remove from heat and quickly stir in egg mixture, adding pasta water as needed
        7. Serve immediately with extra cheese and black pepper

        **Prep time:** 15 minutes
        **Cook time:** 20 minutes
        **Total time:** 35 minutes
        **Servings:** 4
        **Difficulty:** intermediate
        **Cuisine:** italian
        """
        mock_final_response.content = [mock_final_text]

        # Mock citations from search
        mock_citations = [
            {
                "title": "Authentic Carbonara Recipe - Allrecipes",
                "url": "https://allrecipes.com/recipe/carbonara",
                "snippet": "This traditional carbonara recipe is creamy and delicious...",
            },
            {
                "title": "Perfect Carbonara - Food Network",
                "url": "https://foodnetwork.com/recipes/carbonara",
                "snippet": "Learn to make perfect carbonara with this step-by-step guide...",
            },
        ]

        # Setup the mock client to return our responses in sequence
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = [
            mock_initial_response,  # Initial response with search tags
            mock_search_response,  # Search results
            mock_final_response,  # Final structured response
        ]

        # Create services and inject mock client
        anthropic_service = AnthropicService()
        anthropic_service.client = mock_client

        recipe_service = RecipeService()
        recipe_service.anthropic_service = anthropic_service

        # Mock settings
        with patch(
            "src.makemyrecipe.services.anthropic_service.settings"
        ) as mock_settings:
            mock_settings.anthropic_model = "claude-sonnet-4-20250514"
            mock_settings.anthropic_max_tokens = 2000
            mock_settings.anthropic_temperature = 0.7

            # Execute the enhanced recipe search
            recipes, raw_response = await recipe_service.search_recipes_enhanced(
                "I want to make authentic carbonara"
            )

            # Verify the results
            assert len(recipes) >= 1, "Should return at least one recipe"

            recipe = recipes[0]
            assert isinstance(recipe, Recipe), "Should return Recipe objects"

            # Check recipe content
            assert (
                "carbonara" in recipe.title.lower()
            ), "Recipe title should contain 'carbonara'"
            assert len(recipe.ingredients) > 0, "Recipe should have ingredients"
            assert len(recipe.instructions) > 0, "Recipe should have instructions"

            # Check metadata
            assert recipe.prep_time is not None, "Should have prep time"
            assert recipe.cook_time is not None, "Should have cook time"
            assert recipe.servings is not None, "Should have servings"

            # Check that search query is preserved
            assert recipe.search_query == "I want to make authentic carbonara"

            # Check that primary source citation exists
            assert (
                recipe.primary_source is not None
            ), "Should have primary source citation"
            assert isinstance(
                recipe.primary_source, Citation
            ), "Primary source should be Citation object"

            # Check that the recipe has proper timestamps and ID
            assert recipe.id is not None, "Recipe should have an ID"
            assert (
                recipe.created_at is not None
            ), "Recipe should have creation timestamp"
            assert recipe.updated_at is not None, "Recipe should have update timestamp"

            # Verify that multiple API calls were made (search tag workflow)
            assert (
                mock_client.messages.create.call_count == 3
            ), "Should make 3 API calls for search tag workflow"

            # Verify the raw response contains useful information
            assert isinstance(raw_response, str), "Should return raw response string"
            assert len(raw_response) > 0, "Raw response should not be empty"

    @pytest.mark.asyncio
    async def test_search_tag_extraction_and_processing(self):
        """Test that search tags are properly extracted and processed."""

        anthropic_service = AnthropicService()

        # Test search tag extraction
        text_with_tags = """
        I'll help you with that recipe!

        <search>pasta carbonara authentic recipe</search>

        Let me also search for some variations:

        <search>carbonara recipe variations vegetarian</search>

        Here's what I found...
        """

        # Extract search queries
        queries = anthropic_service._extract_search_queries(text_with_tags)

        assert len(queries) == 2, "Should extract 2 search queries"
        assert "pasta carbonara authentic recipe" in queries
        assert "carbonara recipe variations vegetarian" in queries

        # Test search tag removal
        cleaned_text = anthropic_service._remove_search_tags(text_with_tags)

        assert "<search>" not in cleaned_text, "Should remove search tags"
        assert "</search>" not in cleaned_text, "Should remove search tags"
        assert (
            "pasta carbonara authentic recipe" not in cleaned_text
        ), "Should remove search content"
        assert (
            "I'll help you with that recipe!" in cleaned_text
        ), "Should preserve other content"
        assert "Here's what I found..." in cleaned_text, "Should preserve other content"

    @pytest.mark.asyncio
    async def test_recipe_conversion_with_citations(self):
        """Test conversion from RecipeResult to Recipe with proper citations."""

        from src.makemyrecipe.models.recipe import convert_recipe_result_to_recipe
        from src.makemyrecipe.services.recipe_service import (
            CuisineType,
            DifficultyLevel,
            RecipeMetadata,
            RecipeResult,
        )

        # Create a sample RecipeResult
        metadata = RecipeMetadata(
            prep_time=15,
            cook_time=20,
            total_time=35,
            servings=4,
            difficulty=DifficultyLevel.INTERMEDIATE,
            cuisine=CuisineType.ITALIAN,
            calories_per_serving=450,
        )

        recipe_result = RecipeResult(
            title="Test Carbonara",
            description="A test carbonara recipe",
            ingredients=["pasta", "eggs", "cheese"],
            instructions=["cook pasta", "mix eggs", "combine"],
            metadata=metadata,
            source_url="https://example.com/carbonara",
            source_name="Example Cooking Site",
            rating=4.5,
            review_count=100,
        )

        # Convert to Recipe object
        recipe = convert_recipe_result_to_recipe(recipe_result, "test search query")

        # Verify conversion
        assert isinstance(recipe, Recipe)
        assert recipe.title == "Test Carbonara"
        assert recipe.description == "A test carbonara recipe"
        assert recipe.ingredients == ["pasta", "eggs", "cheese"]
        assert recipe.instructions == ["cook pasta", "mix eggs", "combine"]
        assert recipe.prep_time == 15
        assert recipe.cook_time == 20
        assert recipe.total_time == 35
        assert recipe.servings == 4
        assert recipe.difficulty == DifficultyLevel.INTERMEDIATE
        assert recipe.cuisine == CuisineType.ITALIAN
        assert recipe.calories_per_serving == 450
        assert recipe.rating == 4.5
        assert recipe.review_count == 100
        assert recipe.search_query == "test search query"

        # Check primary source citation
        assert recipe.primary_source.title == "Example Cooking Site"
        assert recipe.primary_source.url == "https://example.com/carbonara"
        assert recipe.primary_source.domain == "example.com"

        # Check that additional sources list is empty initially
        assert len(recipe.additional_sources) == 0

        # Test adding additional citations
        additional_citation = Citation(
            title="Another Recipe Source", url="https://another.com/recipe"
        )

        recipe.add_citation(additional_citation)

        assert len(recipe.additional_sources) == 1
        assert recipe.additional_sources[0] == additional_citation

        # Test getting all citations
        all_citations = recipe.get_all_citations()
        assert len(all_citations) == 2
        assert recipe.primary_source in all_citations
        assert additional_citation in all_citations

    def test_system_prompt_includes_search_instructions(self):
        """Test that the system prompt includes proper search tag instructions."""

        anthropic_service = AnthropicService()
        prompt = anthropic_service._create_recipe_system_prompt()

        # Check for key search instruction elements
        assert "search tags" in prompt.lower()
        assert "<search>" in prompt
        assert "</search>" in prompt
        assert "examples of when to use search tags" in prompt.lower()
        assert "search query guidelines" in prompt.lower()
        assert "after searching, always:" in prompt.lower()

        # Check for specific examples
        assert "authentic italian carbonara recipe" in prompt.lower()
        assert "chicken breast recipes with garlic and herbs" in prompt.lower()

        # Check for guidelines
        assert "include specific ingredients" in prompt.lower()
        assert "reputable cooking sites" in prompt.lower()
        assert "source citations with clickable links" in prompt.lower()
