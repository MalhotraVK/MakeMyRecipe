"""Tests for enhanced recipe service functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.makemyrecipe.models.chat import ChatMessage
from src.makemyrecipe.models.recipe import Recipe, Citation
from src.makemyrecipe.services.recipe_service import (
    RecipeService,
    RecipeSearchQuery,
    RecipeResult,
    RecipeMetadata,
    DifficultyLevel,
    CuisineType,
    DietaryRestriction,
)

# Rebuild models to resolve forward references
Recipe.model_rebuild()


class TestEnhancedRecipeService:
    """Test cases for enhanced recipe service functionality."""

    @pytest.fixture
    def recipe_service(self):
        """Create a RecipeService instance for testing."""
        return RecipeService()

    @pytest.fixture
    def sample_recipe_result(self):
        """Create a sample RecipeResult for testing."""
        metadata = RecipeMetadata(
            prep_time=15,
            cook_time=20,
            total_time=35,
            servings=4,
            difficulty=DifficultyLevel.INTERMEDIATE,
            cuisine=CuisineType.ITALIAN,
            dietary_restrictions=[],
            calories_per_serving=450
        )
        
        return RecipeResult(
            title="Spaghetti Carbonara",
            description="Classic Italian pasta dish",
            ingredients=["400g spaghetti", "200g pancetta", "4 eggs", "100g parmesan"],
            instructions=["Boil pasta", "Cook pancetta", "Mix eggs and cheese", "Combine all"],
            metadata=metadata,
            source_url="https://allrecipes.com/carbonara",
            source_name="Allrecipes",
            rating=4.5,
            review_count=1250
        )

    @pytest.fixture
    def sample_citations(self):
        """Create sample citations for testing."""
        return [
            {
                "title": "Best Carbonara Recipe - Allrecipes",
                "url": "https://allrecipes.com/carbonara",
                "snippet": "This authentic carbonara recipe is creamy and delicious..."
            },
            {
                "title": "Perfect Carbonara - Food Network",
                "url": "https://foodnetwork.com/carbonara",
                "snippet": "Learn how to make perfect carbonara with this guide..."
            }
        ]

    @pytest.mark.asyncio
    async def test_search_recipes_enhanced_success(self, recipe_service, sample_recipe_result):
        """Test successful enhanced recipe search."""
        # Mock the regular search_recipes method
        with patch.object(recipe_service, 'search_recipes') as mock_search:
            mock_search.return_value = ([sample_recipe_result], "Raw response content")
            
            recipes, raw_response = await recipe_service.search_recipes_enhanced(
                "carbonara recipe"
            )
            
            assert len(recipes) == 1
            assert isinstance(recipes[0], Recipe)
            assert recipes[0].title == "Spaghetti Carbonara"
            assert recipes[0].description == "Classic Italian pasta dish"
            assert len(recipes[0].ingredients) == 4
            assert len(recipes[0].instructions) == 4
            assert recipes[0].prep_time == 15
            assert recipes[0].cook_time == 20
            assert recipes[0].total_time == 35
            assert recipes[0].servings == 4
            assert recipes[0].difficulty == DifficultyLevel.INTERMEDIATE
            assert recipes[0].cuisine == CuisineType.ITALIAN
            assert recipes[0].calories_per_serving == 450
            assert recipes[0].rating == 4.5
            assert recipes[0].review_count == 1250
            assert recipes[0].search_query == "carbonara recipe"
            
            # Check primary source citation
            assert recipes[0].primary_source.title == "Allrecipes"
            assert recipes[0].primary_source.url == "https://allrecipes.com/carbonara"
            assert recipes[0].primary_source.domain == "allrecipes.com"
            
            assert raw_response == "Raw response content"
            
            # Verify the underlying search was called correctly
            mock_search.assert_called_once_with("carbonara recipe", None)

    @pytest.mark.asyncio
    async def test_search_recipes_enhanced_with_query_params(self, recipe_service, sample_recipe_result):
        """Test enhanced recipe search with query parameters."""
        query_params = RecipeSearchQuery(
            ingredients=["pasta", "eggs"],
            cuisine=CuisineType.ITALIAN,
            difficulty=DifficultyLevel.INTERMEDIATE,
            max_prep_time=30
        )
        
        with patch.object(recipe_service, 'search_recipes') as mock_search:
            mock_search.return_value = ([sample_recipe_result], "Raw response")
            
            recipes, raw_response = await recipe_service.search_recipes_enhanced(
                "pasta with eggs", query_params
            )
            
            assert len(recipes) == 1
            assert isinstance(recipes[0], Recipe)
            assert recipes[0].search_query == "pasta with eggs"
            
            # Verify the query params were passed through
            mock_search.assert_called_once_with("pasta with eggs", query_params)

    @pytest.mark.asyncio
    async def test_search_recipes_enhanced_multiple_results(self, recipe_service):
        """Test enhanced recipe search with multiple results."""
        # Create multiple recipe results
        metadata1 = RecipeMetadata(
            prep_time=15, cook_time=20, servings=4,
            difficulty=DifficultyLevel.INTERMEDIATE, cuisine=CuisineType.ITALIAN
        )
        metadata2 = RecipeMetadata(
            prep_time=10, cook_time=15, servings=2,
            difficulty=DifficultyLevel.BEGINNER, cuisine=CuisineType.ITALIAN
        )
        
        recipe_result1 = RecipeResult(
            title="Carbonara Recipe 1", description="Description 1",
            ingredients=["ingredient1"], instructions=["instruction1"],
            metadata=metadata1, source_url="https://site1.com", source_name="Site 1"
        )
        recipe_result2 = RecipeResult(
            title="Carbonara Recipe 2", description="Description 2",
            ingredients=["ingredient2"], instructions=["instruction2"],
            metadata=metadata2, source_url="https://site2.com", source_name="Site 2"
        )
        
        with patch.object(recipe_service, 'search_recipes') as mock_search:
            mock_search.return_value = ([recipe_result1, recipe_result2], "Raw response")
            
            recipes, raw_response = await recipe_service.search_recipes_enhanced(
                "carbonara recipes"
            )
            
            assert len(recipes) == 2
            assert all(isinstance(recipe, Recipe) for recipe in recipes)
            
            assert recipes[0].title == "Carbonara Recipe 1"
            assert recipes[1].title == "Carbonara Recipe 2"
            
            assert recipes[0].primary_source.domain == "site1.com"
            assert recipes[1].primary_source.domain == "site2.com"

    @pytest.mark.asyncio
    async def test_search_recipes_enhanced_empty_results(self, recipe_service):
        """Test enhanced recipe search with no results."""
        with patch.object(recipe_service, 'search_recipes') as mock_search:
            mock_search.return_value = ([], "No recipes found")
            
            recipes, raw_response = await recipe_service.search_recipes_enhanced(
                "nonexistent recipe"
            )
            
            assert len(recipes) == 0
            assert raw_response == "No recipes found"

    @pytest.mark.asyncio
    async def test_search_recipes_enhanced_error_handling(self, recipe_service):
        """Test enhanced recipe search error handling."""
        with patch.object(recipe_service, 'search_recipes') as mock_search:
            mock_search.side_effect = Exception("Search failed")
            
            with pytest.raises(Exception, match="Search failed"):
                await recipe_service.search_recipes_enhanced("test query")

    def test_parse_recipe_response_with_search_query(self, recipe_service, sample_citations):
        """Test recipe response parsing with search query parameter."""
        content = """
        **Spaghetti Carbonara**
        
        A classic Italian pasta dish that's creamy and delicious.
        
        **Ingredients:**
        - 400g spaghetti
        - 200g pancetta
        - 4 large eggs
        - 100g parmesan cheese
        
        **Instructions:**
        1. Boil the pasta in salted water
        2. Cook pancetta until crispy
        3. Mix eggs with parmesan
        4. Combine everything while hot
        
        **Prep time:** 15 minutes
        **Cook time:** 20 minutes
        **Servings:** 4
        **Difficulty:** intermediate
        """
        
        search_query = "carbonara recipe"
        recipes = recipe_service._parse_recipe_response(content, sample_citations, search_query)
        
        assert len(recipes) == 1
        recipe = recipes[0]
        
        assert recipe.title == "Spaghetti Carbonara"
        assert "classic italian pasta" in recipe.description.lower()
        assert len(recipe.ingredients) == 4
        assert len(recipe.instructions) == 4
        assert recipe.metadata.prep_time == 15
        assert recipe.metadata.cook_time == 20
        assert recipe.metadata.servings == 4
        assert recipe.metadata.difficulty == DifficultyLevel.INTERMEDIATE

    @pytest.mark.asyncio
    async def test_search_recipes_integration_with_anthropic_service(self, recipe_service):
        """Test integration between recipe service and anthropic service."""
        # Mock the anthropic service
        mock_anthropic_service = AsyncMock()
        mock_anthropic_service.generate_recipe_response.return_value = (
            """
            **Classic Carbonara**
            
            Traditional Italian pasta dish.
            
            **Ingredients:**
            - 400g spaghetti
            - 200g guanciale
            
            **Instructions:**
            1. Cook pasta
            2. Prepare sauce
            
            **Prep time:** 15 minutes
            **Cook time:** 20 minutes
            **Servings:** 4
            """,
            [
                {
                    "title": "Carbonara Recipe - Allrecipes",
                    "url": "https://allrecipes.com/carbonara",
                    "snippet": "Authentic carbonara recipe"
                }
            ]
        )
        
        recipe_service.anthropic_service = mock_anthropic_service
        
        recipes, raw_response = await recipe_service.search_recipes("carbonara recipe")
        
        assert len(recipes) >= 1
        assert "Classic Carbonara" in recipes[0].title
        
        # Verify anthropic service was called with correct parameters
        mock_anthropic_service.generate_recipe_response.assert_called_once()
        call_args = mock_anthropic_service.generate_recipe_response.call_args
        assert call_args[1]["use_web_search"] is True
        
        # Check that the messages contain the recipe prompt
        messages = call_args.kwargs["messages"]  # Check keyword arguments
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert "carbonara recipe" in messages[0].content.lower()

    def test_recipe_service_trusted_domains(self, recipe_service):
        """Test that recipe service has trusted domains configured."""
        assert len(recipe_service.TRUSTED_DOMAINS) > 0
        assert "allrecipes.com" in recipe_service.TRUSTED_DOMAINS
        assert "foodnetwork.com" in recipe_service.TRUSTED_DOMAINS
        assert "seriouseats.com" in recipe_service.TRUSTED_DOMAINS

    def test_build_search_query_with_domain_filtering(self, recipe_service):
        """Test that search queries include domain filtering."""
        query_params = RecipeSearchQuery(
            ingredients=["pasta"],
            cuisine=CuisineType.ITALIAN
        )
        
        search_query = recipe_service._build_search_query(query_params, "carbonara recipe")
        
        assert "carbonara recipe" in search_query
        assert "pasta" in search_query
        assert "italian cuisine" in search_query
        assert "site:allrecipes.com" in search_query
        assert "site:foodnetwork.com" in search_query
        assert " OR " in search_query  # Domain filtering uses OR

    def test_create_recipe_prompt_comprehensive(self, recipe_service):
        """Test that recipe prompts are comprehensive and well-structured."""
        query_params = RecipeSearchQuery(
            ingredients=["chicken", "garlic"],
            exclude_ingredients=["dairy"],
            cuisine=CuisineType.MEDITERRANEAN,
            dietary_restrictions=[DietaryRestriction.DAIRY_FREE],
            difficulty=DifficultyLevel.INTERMEDIATE,
            max_prep_time=30,
            max_cook_time=45,
            servings=4,
            recipe_type="main course"
        )
        
        prompt = recipe_service._create_recipe_prompt(query_params, "chicken dinner")
        
        assert "MakeMyRecipe" in prompt
        assert "chicken dinner" in prompt
        assert "chicken, garlic" in prompt
        assert "dairy" in prompt
        assert "mediterranean" in prompt
        assert "dairy free" in prompt
        assert "intermediate" in prompt
        assert "30 minutes" in prompt
        assert "45 minutes" in prompt
        assert "4" in prompt
        assert "main course" in prompt
        assert "ingredient list" in prompt.lower()
        assert "instructions" in prompt.lower()
        assert "source" in prompt.lower()