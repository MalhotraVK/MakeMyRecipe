"""Tests for enhanced recipe API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.makemyrecipe.api.main import app
from src.makemyrecipe.models.recipe import (
    Citation,
    CuisineRecipeRequest,
    EnhancedRecipeSearchResponse,
    IngredientSuggestionRequest,
    Recipe,
    RecipeSearchRequest,
    RecipeSearchResponse,
)
from src.makemyrecipe.services.recipe_service import (
    CuisineType,
    DietaryRestriction,
    DifficultyLevel,
)

# Rebuild models to resolve forward references
Recipe.model_rebuild()
RecipeSearchRequest.model_rebuild()
RecipeSearchResponse.model_rebuild()
EnhancedRecipeSearchResponse.model_rebuild()
IngredientSuggestionRequest.model_rebuild()
CuisineRecipeRequest.model_rebuild()


class TestEnhancedRecipeAPI:
    """Test cases for enhanced recipe API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def sample_recipe(self):
        """Create a sample Recipe object for testing."""
        primary_source = Citation(
            title="Best Carbonara - Allrecipes",
            url="https://allrecipes.com/carbonara",
            domain="allrecipes.com",
            snippet="Authentic Italian carbonara recipe",
        )

        return Recipe(
            title="Spaghetti Carbonara",
            description="Classic Italian pasta dish with eggs, cheese, and pancetta",
            ingredients=[
                "400g spaghetti",
                "200g pancetta, diced",
                "4 large eggs",
                "100g Parmesan cheese, grated",
                "Black pepper to taste",
            ],
            instructions=[
                "Bring a large pot of salted water to boil and cook spaghetti",
                "Cook pancetta in a large skillet until crispy",
                "Whisk eggs with Parmesan cheese in a bowl",
                "Drain pasta and immediately toss with pancetta",
                "Remove from heat and quickly stir in egg mixture",
                "Season with black pepper and serve immediately",
            ],
            prep_time=15,
            cook_time=20,
            total_time=35,
            servings=4,
            difficulty=DifficultyLevel.INTERMEDIATE,
            cuisine=CuisineType.ITALIAN,
            dietary_restrictions=[],
            calories_per_serving=450,
            primary_source=primary_source,
            rating=4.5,
            review_count=1250,
            search_query="carbonara recipe",
        )

    def test_enhanced_search_endpoint_exists(self, client):
        """Test that the enhanced search endpoint exists."""
        response = client.post("/recipes/search/enhanced", json={"query": "test query"})

        # Should not return 404 (endpoint exists)
        assert response.status_code != 404

    @patch("src.makemyrecipe.api.routes.recipe.recipe_service")
    def test_enhanced_search_success(self, mock_recipe_service, client, sample_recipe):
        """Test successful enhanced recipe search."""
        # Mock the enhanced search method
        mock_recipe_service.search_recipes_enhanced = AsyncMock(
            return_value=([sample_recipe], "Raw AI response content")
        )

        response = client.post(
            "/recipes/search/enhanced",
            json={
                "query": "carbonara recipe",
                "cuisine": "italian",
                "difficulty": "intermediate",
                "max_prep_time": 30,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "recipes" in data
        assert "total_count" in data
        assert "search_query" in data
        assert "raw_response" in data

        # Check response values
        assert data["total_count"] == 1
        assert data["search_query"] == "carbonara recipe"
        assert data["raw_response"] == "Raw AI response content"

        # Check recipe data
        recipes = data["recipes"]
        assert len(recipes) == 1

        recipe = recipes[0]
        assert recipe["title"] == "Spaghetti Carbonara"
        assert (
            recipe["description"]
            == "Classic Italian pasta dish with eggs, cheese, and pancetta"
        )
        assert len(recipe["ingredients"]) == 5
        assert len(recipe["instructions"]) == 6
        assert recipe["prep_time"] == 15
        assert recipe["cook_time"] == 20
        assert recipe["total_time"] == 35
        assert recipe["servings"] == 4
        assert recipe["difficulty"] == "intermediate"
        assert recipe["cuisine"] == "italian"
        assert recipe["calories_per_serving"] == 450
        assert recipe["rating"] == 4.5
        assert recipe["review_count"] == 1250
        assert recipe["search_query"] == "carbonara recipe"
        assert recipe["is_saved"] is False

        # Check primary source citation
        primary_source = recipe["primary_source"]
        assert primary_source["title"] == "Best Carbonara - Allrecipes"
        assert primary_source["url"] == "https://allrecipes.com/carbonara"
        assert primary_source["domain"] == "allrecipes.com"
        assert primary_source["snippet"] == "Authentic Italian carbonara recipe"

        # Check that additional_sources is present (even if empty)
        assert "additional_sources" in recipe
        assert isinstance(recipe["additional_sources"], list)

        # Check timestamps are present
        assert "created_at" in recipe
        assert "updated_at" in recipe
        assert "id" in recipe

    @patch("src.makemyrecipe.api.routes.recipe.recipe_service")
    def test_enhanced_search_multiple_recipes(
        self, mock_recipe_service, client, sample_recipe
    ):
        """Test enhanced search with multiple recipes."""
        # Create a second recipe
        second_recipe = Recipe(
            title="Vegetarian Carbonara",
            description="Plant-based version of classic carbonara",
            ingredients=["400g pasta", "200g mushrooms", "3 eggs", "100g vegan cheese"],
            instructions=[
                "Cook pasta",
                "Sauté mushrooms",
                "Mix eggs and cheese",
                "Combine",
            ],
            prep_time=10,
            cook_time=15,
            servings=4,
            difficulty=DifficultyLevel.BEGINNER,
            cuisine=CuisineType.ITALIAN,
            dietary_restrictions=[DietaryRestriction.VEGETARIAN],
            primary_source=Citation(
                title="Vegan Carbonara - Plant Based",
                url="https://plantbased.com/carbonara",
            ),
            search_query="vegetarian carbonara",
        )

        mock_recipe_service.search_recipes_enhanced = AsyncMock(
            return_value=([sample_recipe, second_recipe], "Multiple recipes found")
        )

        response = client.post(
            "/recipes/search/enhanced",
            json={"query": "carbonara recipes", "dietary_restrictions": ["vegetarian"]},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 2
        assert len(data["recipes"]) == 2

        # Check that both recipes are present
        titles = [recipe["title"] for recipe in data["recipes"]]
        assert "Spaghetti Carbonara" in titles
        assert "Vegetarian Carbonara" in titles

    @patch("src.makemyrecipe.api.routes.recipe.recipe_service")
    def test_enhanced_search_empty_results(self, mock_recipe_service, client):
        """Test enhanced search with no results."""
        mock_recipe_service.search_recipes_enhanced = AsyncMock(
            return_value=([], "No recipes found matching your criteria")
        )

        response = client.post(
            "/recipes/search/enhanced", json={"query": "nonexistent recipe"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 0
        assert len(data["recipes"]) == 0
        assert data["search_query"] == "nonexistent recipe"
        assert "No recipes found" in data["raw_response"]

    @patch("src.makemyrecipe.api.routes.recipe.recipe_service")
    def test_enhanced_search_service_error(self, mock_recipe_service, client):
        """Test enhanced search when service raises an error."""
        mock_recipe_service.search_recipes_enhanced = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        response = client.post(
            "/recipes/search/enhanced", json={"query": "test recipe"}
        )

        assert response.status_code == 500
        data = response.json()
        assert "Enhanced recipe search failed" in data["detail"]
        assert "Service unavailable" in data["detail"]

    def test_enhanced_search_invalid_request(self, client):
        """Test enhanced search with invalid request data."""
        response = client.post(
            "/recipes/search/enhanced",
            json={
                # Missing required 'query' field
                "cuisine": "italian"
            },
        )

        assert response.status_code == 422  # Validation error

    def test_enhanced_search_request_validation(self, client):
        """Test enhanced search request validation."""
        response = client.post(
            "/recipes/search/enhanced",
            json={
                "query": "pasta recipe",
                "ingredients": ["pasta", "tomatoes"],
                "exclude_ingredients": ["mushrooms"],
                "cuisine": "italian",
                "dietary_restrictions": ["vegetarian", "gluten_free"],
                "difficulty": "intermediate",
                "max_prep_time": 30,
                "max_cook_time": 45,
                "servings": 4,
                "recipe_type": "main course",
            },
        )

        # Should not return validation error
        assert response.status_code != 422

    @patch("src.makemyrecipe.api.routes.recipe.recipe_service")
    def test_enhanced_search_with_citations(self, mock_recipe_service, client):
        """Test enhanced search response includes proper citations."""
        # Create recipe with additional citations
        recipe_with_citations = Recipe(
            title="Carbonara with Citations",
            description="Well-sourced carbonara recipe",
            ingredients=["pasta", "eggs"],
            instructions=["cook", "mix"],
            primary_source=Citation(
                title="Primary Source",
                url="https://primary.com/recipe",
                domain="primary.com",
            ),
            additional_sources=[
                Citation(
                    title="Additional Source 1",
                    url="https://additional1.com/recipe",
                    domain="additional1.com",
                    snippet="Great additional info",
                ),
                Citation(
                    title="Additional Source 2",
                    url="https://additional2.com/recipe",
                    domain="additional2.com",
                ),
            ],
        )

        mock_recipe_service.search_recipes_enhanced = AsyncMock(
            return_value=([recipe_with_citations], "Response with citations")
        )

        response = client.post(
            "/recipes/search/enhanced", json={"query": "well-sourced carbonara"}
        )

        assert response.status_code == 200
        data = response.json()

        recipe = data["recipes"][0]

        # Check primary source
        primary_source = recipe["primary_source"]
        assert primary_source["title"] == "Primary Source"
        assert primary_source["url"] == "https://primary.com/recipe"
        assert primary_source["domain"] == "primary.com"

        # Check additional sources
        additional_sources = recipe["additional_sources"]
        assert len(additional_sources) == 2

        assert additional_sources[0]["title"] == "Additional Source 1"
        assert additional_sources[0]["url"] == "https://additional1.com/recipe"
        assert additional_sources[0]["snippet"] == "Great additional info"

        assert additional_sources[1]["title"] == "Additional Source 2"
        assert additional_sources[1]["url"] == "https://additional2.com/recipe"

    def test_enhanced_search_response_model_validation(self, client):
        """Test that the enhanced search response follows the correct model."""
        # This test ensures the response model is properly defined
        # by checking the OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})
        enhanced_search_path = paths.get("/recipes/search/enhanced", {})
        post_method = enhanced_search_path.get("post", {})
        responses = post_method.get("responses", {})
        success_response = responses.get("200", {})
        content = success_response.get("content", {})
        json_content = content.get("application/json", {})
        schema_ref = json_content.get("schema", {}).get("$ref", "")

        # Should reference the EnhancedRecipeSearchResponse model
        assert "EnhancedRecipeSearchResponse" in schema_ref

    @patch("src.makemyrecipe.api.routes.recipe.recipe_service")
    def test_enhanced_search_preserves_search_query(
        self, mock_recipe_service, client, sample_recipe
    ):
        """Test that the search query is preserved in the response."""
        original_query = "authentic italian carbonara with guanciale"

        mock_recipe_service.search_recipes_enhanced = AsyncMock(
            return_value=([sample_recipe], "Search results")
        )

        response = client.post(
            "/recipes/search/enhanced", json={"query": original_query}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["search_query"] == original_query

        # Verify the service was called with the correct query
        mock_recipe_service.search_recipes_enhanced.assert_called_once()
        call_args = mock_recipe_service.search_recipes_enhanced.call_args
        # Check keyword arguments instead
        assert call_args.kwargs["user_query"] == original_query
