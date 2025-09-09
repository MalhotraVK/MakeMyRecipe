"""Tests for recipe service functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.makemyrecipe.models.chat import ChatMessage
from src.makemyrecipe.services.recipe_service import (
    CuisineType,
    DietaryRestriction,
    DifficultyLevel,
    RecipeMetadata,
    RecipeResult,
    RecipeSearchQuery,
    RecipeService,
)


class TestRecipeService:
    """Test cases for RecipeService."""

    @pytest.fixture
    def recipe_service(self) -> RecipeService:
        """Create a RecipeService instance for testing."""
        return RecipeService()

    @pytest.fixture
    def mock_anthropic_response(self) -> tuple:
        """Mock Anthropic service response."""
        content = """
        **Spaghetti Carbonara**

        A classic Italian pasta dish with eggs, cheese, and pancetta.

        **Ingredients:**
        - 400g spaghetti
        - 200g pancetta, diced
        - 4 large eggs
        - 100g Pecorino Romano cheese, grated
        - Black pepper to taste
        - Salt for pasta water

        **Instructions:**
        1. Bring a large pot of salted water to boil and cook spaghetti 
           according to package directions.
        2. While pasta cooks, fry pancetta in a large skillet until crispy.
        3. In a bowl, whisk together eggs, cheese, and black pepper.
        4. Drain pasta, reserving 1 cup pasta water.
        5. Add hot pasta to the skillet with pancetta.
        6. Remove from heat and quickly stir in egg mixture, adding pasta 
           water as needed.
        7. Serve immediately with extra cheese and pepper.

        **Prep time:** 15 minutes
        **Cook time:** 20 minutes
        **Total time:** 35 minutes
        **Servings:** 4
        **Difficulty:** Intermediate
        """

        citations = [
            {
                "title": "Classic Spaghetti Carbonara Recipe",
                "url": "https://www.seriouseats.com/spaghetti-carbonara-recipe",
                "snippet": "The ultimate guide to making authentic carbonara",
            }
        ]

        return content, citations

    def test_domain_filter_string(self, recipe_service: RecipeService) -> None:
        """Test domain filter string generation."""
        domain_filter = recipe_service._create_domain_filter_string()

        assert "site:allrecipes.com" in domain_filter
        assert "site:foodnetwork.com" in domain_filter
        assert "site:seriouseats.com" in domain_filter
        assert " OR " in domain_filter

    def test_build_search_query_basic(self, recipe_service: RecipeService) -> None:
        """Test basic search query building."""
        query = RecipeSearchQuery(
            ingredients=["chicken", "rice"],
            cuisine=CuisineType.ITALIAN,
        )

        search_query = recipe_service._build_search_query(query, "chicken rice recipe")

        assert "chicken rice recipe" in search_query
        assert "recipe with chicken rice" in search_query
        assert "italian cuisine" in search_query
        assert "site:allrecipes.com" in search_query

    def test_build_search_query_with_restrictions(
        self, recipe_service: RecipeService
    ) -> None:
        """Test search query building with dietary restrictions."""
        query = RecipeSearchQuery(
            ingredients=["tofu"],
            dietary_restrictions=[
                DietaryRestriction.VEGAN,
                DietaryRestriction.GLUTEN_FREE,
            ],
            difficulty=DifficultyLevel.BEGINNER,
            max_prep_time=30,
            exclude_ingredients=["nuts"],
        )

        search_query = recipe_service._build_search_query(query, "easy tofu recipe")

        assert "easy tofu recipe" in search_query
        assert "vegan" in search_query
        assert "gluten free" in search_query
        assert "beginner recipe" in search_query
        assert "quick 30 minutes" in search_query
        assert "-nuts" in search_query

    def test_create_recipe_prompt(self, recipe_service: RecipeService) -> None:
        """Test recipe prompt creation."""
        query = RecipeSearchQuery(
            ingredients=["pasta", "tomatoes"],
            cuisine=CuisineType.ITALIAN,
            dietary_restrictions=[DietaryRestriction.VEGETARIAN],
            difficulty=DifficultyLevel.INTERMEDIATE,
            servings=4,
        )

        prompt = recipe_service._create_recipe_prompt(query, "pasta with tomatoes")

        assert "pasta with tomatoes" in prompt
        assert "pasta, tomatoes" in prompt
        assert "italian" in prompt
        assert "vegetarian" in prompt
        assert "intermediate" in prompt
        assert "4" in prompt
        assert "step-by-step" in prompt.lower()
        assert "trusted cooking websites" in prompt

    def test_extract_recipe_metadata(self, recipe_service: RecipeService) -> None:
        """Test recipe metadata extraction."""
        content = """
        This is a delicious intermediate Italian recipe.
        Prep time: 15 minutes
        Cook time: 25 minutes
        Total time: 40 minutes
        Serves: 6 people
        Calories: 450 per serving
        This recipe is vegetarian and gluten free.
        """

        metadata = recipe_service._extract_recipe_metadata(content)

        assert metadata.prep_time == 15
        assert metadata.cook_time == 25
        assert metadata.total_time == 40
        assert metadata.servings == 6
        assert metadata.difficulty == DifficultyLevel.INTERMEDIATE
        assert metadata.cuisine == CuisineType.ITALIAN
        assert metadata.calories_per_serving == 450
        assert DietaryRestriction.VEGETARIAN in metadata.dietary_restrictions
        assert DietaryRestriction.GLUTEN_FREE in metadata.dietary_restrictions

    def test_parse_recipe_response(
        self, recipe_service: RecipeService, mock_anthropic_response: tuple
    ) -> None:
        """Test recipe response parsing."""
        content, citations = mock_anthropic_response

        recipes = recipe_service._parse_recipe_response(content, citations)

        assert len(recipes) == 1
        recipe = recipes[0]

        assert recipe.title == "Spaghetti Carbonara"
        assert "classic Italian pasta dish" in recipe.description
        assert len(recipe.ingredients) > 0
        assert "400g spaghetti" in recipe.ingredients
        assert len(recipe.instructions) > 0
        assert "Bring a large pot" in recipe.instructions[0]
        assert recipe.metadata.prep_time == 15
        assert recipe.metadata.cook_time == 20
        assert recipe.metadata.total_time == 35
        assert recipe.metadata.servings == 4
        assert recipe.metadata.difficulty == DifficultyLevel.INTERMEDIATE
        assert (
            recipe.source_url
            == "https://www.seriouseats.com/spaghetti-carbonara-recipe"
        )

    @pytest.mark.asyncio
    async def test_search_recipes_success(
        self, recipe_service: RecipeService, mock_anthropic_response: tuple
    ) -> None:
        """Test successful recipe search."""
        content, citations = mock_anthropic_response

        with patch.object(
            recipe_service.anthropic_service,
            "generate_recipe_response",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = (content, citations)

            query = RecipeSearchQuery(ingredients=["pasta"])
            recipes, raw_response = await recipe_service.search_recipes(
                "pasta recipe", query
            )

            assert len(recipes) == 1
            assert recipes[0].title == "Spaghetti Carbonara"
            assert raw_response == content

            # Verify the anthropic service was called correctly
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            assert call_args[1]["use_web_search"] is True
            assert len(call_args[1]["messages"]) == 1
            assert "pasta recipe" in call_args[1]["messages"][0].content

    @pytest.mark.asyncio
    async def test_search_recipes_error_handling(
        self, recipe_service: RecipeService
    ) -> None:
        """Test recipe search error handling."""
        with patch.object(
            recipe_service.anthropic_service,
            "generate_recipe_response",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.side_effect = Exception("API Error")

            recipes, raw_response = await recipe_service.search_recipes("test query")

            assert len(recipes) == 0
            assert "error" in raw_response.lower()

    @pytest.mark.asyncio
    async def test_get_recipe_suggestions(
        self, recipe_service: RecipeService, mock_anthropic_response: tuple
    ) -> None:
        """Test ingredient-based recipe suggestions."""
        content, citations = mock_anthropic_response

        with patch.object(
            recipe_service.anthropic_service,
            "generate_recipe_response",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = (content, citations)

            ingredients = ["chicken", "rice", "vegetables"]
            dietary_restrictions = [DietaryRestriction.GLUTEN_FREE]

            recipes, raw_response = await recipe_service.get_recipe_suggestions(
                ingredients, dietary_restrictions
            )

            assert len(recipes) == 1
            assert raw_response == content

            # Verify the call was made with correct parameters
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            # Check keyword arguments instead of positional
            assert call_args[1]["use_web_search"] is True
            messages = call_args[1]["messages"]
            assert len(messages) == 1
            assert "chicken, rice, vegetables" in messages[0].content

    @pytest.mark.asyncio
    async def test_get_cuisine_recipes(
        self, recipe_service: RecipeService, mock_anthropic_response: tuple
    ) -> None:
        """Test cuisine-specific recipe search."""
        content, citations = mock_anthropic_response

        with patch.object(
            recipe_service.anthropic_service,
            "generate_recipe_response",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = (content, citations)

            recipes, raw_response = await recipe_service.get_cuisine_recipes(
                CuisineType.ITALIAN, DifficultyLevel.BEGINNER
            )

            assert len(recipes) == 1
            assert raw_response == content

            # Verify the call was made with correct parameters
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            # Check keyword arguments instead of positional
            assert call_args[1]["use_web_search"] is True
            messages = call_args[1]["messages"]
            assert len(messages) == 1
            assert "italian recipes" in messages[0].content
            assert "beginner level" in messages[0].content

    def test_optimize_search_query(self, recipe_service: RecipeService) -> None:
        """Test search query optimization."""
        original_query = (
            "I want to make a delicious pasta dish with tomatoes and cheese"
        )
        optimized = recipe_service.optimize_search_query(original_query)

        # Should remove stop words and add recipe term
        assert "the" not in optimized
        assert "want" not in optimized
        assert "make" in optimized or "recipe" in optimized
        assert "pasta" in optimized
        assert "tomatoes" in optimized
        assert "cheese" in optimized

    def test_trusted_domains_list(self, recipe_service: RecipeService) -> None:
        """Test that trusted domains list is properly configured."""
        domains = recipe_service.TRUSTED_DOMAINS

        assert len(domains) > 0
        assert "allrecipes.com" in domains
        assert "foodnetwork.com" in domains
        assert "seriouseats.com" in domains
        assert "bonappetit.com" in domains

        # Ensure all domains are properly formatted
        for domain in domains:
            assert "." in domain
            assert not domain.startswith("http")
            assert not domain.startswith("www")


class TestRecipeModels:
    """Test cases for recipe data models."""

    def test_recipe_metadata_defaults(self) -> None:
        """Test RecipeMetadata default values."""
        metadata = RecipeMetadata()

        assert metadata.prep_time is None
        assert metadata.cook_time is None
        assert metadata.total_time is None
        assert metadata.servings is None
        assert metadata.difficulty is None
        assert metadata.cuisine is None
        assert metadata.dietary_restrictions == []
        assert metadata.calories_per_serving is None

    def test_recipe_search_query_defaults(self) -> None:
        """Test RecipeSearchQuery default values."""
        query = RecipeSearchQuery()

        assert query.ingredients == []
        assert query.cuisine is None
        assert query.dietary_restrictions == []
        assert query.difficulty is None
        assert query.max_prep_time is None
        assert query.max_cook_time is None
        assert query.servings is None
        assert query.exclude_ingredients == []
        assert query.recipe_type is None

    def test_recipe_result_creation(self) -> None:
        """Test RecipeResult creation."""
        metadata = RecipeMetadata(
            prep_time=15,
            cook_time=30,
            servings=4,
            difficulty=DifficultyLevel.INTERMEDIATE,
        )

        recipe = RecipeResult(
            title="Test Recipe",
            description="A test recipe",
            ingredients=["ingredient1", "ingredient2"],
            instructions=["step1", "step2"],
            metadata=metadata,
            source_url="https://example.com",
            source_name="Example Site",
            rating=4.5,
            review_count=100,
        )

        assert recipe.title == "Test Recipe"
        assert recipe.description == "A test recipe"
        assert len(recipe.ingredients) == 2
        assert len(recipe.instructions) == 2
        assert recipe.metadata.prep_time == 15
        assert recipe.metadata.difficulty == DifficultyLevel.INTERMEDIATE
        assert recipe.source_url == "https://example.com"
        assert recipe.rating == 4.5
        assert recipe.review_count == 100


class TestRecipeEnums:
    """Test cases for recipe enums."""

    def test_difficulty_level_enum(self) -> None:
        """Test DifficultyLevel enum values."""
        assert DifficultyLevel.BEGINNER == "beginner"
        assert DifficultyLevel.INTERMEDIATE == "intermediate"
        assert DifficultyLevel.ADVANCED == "advanced"

    def test_cuisine_type_enum(self) -> None:
        """Test CuisineType enum values."""
        assert CuisineType.ITALIAN == "italian"
        assert CuisineType.CHINESE == "chinese"
        assert CuisineType.MEXICAN == "mexican"
        assert CuisineType.INDIAN == "indian"

        # Test that all enum values are lowercase and use underscores
        for cuisine in CuisineType:
            assert cuisine.value.islower()
            assert " " not in cuisine.value

    def test_dietary_restriction_enum(self) -> None:
        """Test DietaryRestriction enum values."""
        assert DietaryRestriction.VEGETARIAN == "vegetarian"
        assert DietaryRestriction.VEGAN == "vegan"
        assert DietaryRestriction.GLUTEN_FREE == "gluten_free"
        assert DietaryRestriction.DAIRY_FREE == "dairy_free"

        # Test that all enum values are lowercase and use underscores
        for restriction in DietaryRestriction:
            assert restriction.value.islower()
            assert " " not in restriction.value
