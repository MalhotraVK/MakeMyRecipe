"""Tests for recipe API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.makemyrecipe.api.main import create_app
from src.makemyrecipe.services.recipe_service import (
    CuisineType,
    DietaryRestriction,
    DifficultyLevel,
    RecipeMetadata,
    RecipeResult,
)


class TestRecipeAPI:
    """Test cases for recipe API endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def mock_recipe_result(self) -> RecipeResult:
        """Create a mock recipe result for testing."""
        metadata = RecipeMetadata(
            prep_time=15,
            cook_time=30,
            total_time=45,
            servings=4,
            difficulty=DifficultyLevel.INTERMEDIATE,
            cuisine=CuisineType.ITALIAN,
            dietary_restrictions=[DietaryRestriction.VEGETARIAN],
            calories_per_serving=350,
        )

        return RecipeResult(
            title="Spaghetti Carbonara",
            description="A classic Italian pasta dish",
            ingredients=["400g spaghetti", "200g pancetta", "4 eggs", "100g cheese"],
            instructions=[
                "Boil water and cook pasta",
                "Fry pancetta until crispy",
                "Mix eggs and cheese",
                "Combine everything",
            ],
            metadata=metadata,
            source_url="https://www.seriouseats.com/carbonara",
            source_name="Serious Eats",
            rating=4.8,
            review_count=256,
        )

    @pytest.mark.asyncio
    async def test_search_recipes_success(
        self, client: TestClient, mock_recipe_result: RecipeResult
    ) -> None:
        """Test successful recipe search."""
        with patch(
            "src.makemyrecipe.services.recipe_service.recipe_service.search_recipes"
        ) as mock_search:
            mock_search.return_value = ([mock_recipe_result], "Raw response content")

            response = client.post(
                "/recipes/search",
                json={
                    "query": "pasta recipe",
                    "cuisine": "italian",
                    "difficulty": "intermediate",
                    "max_prep_time": 30,
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert data["total_count"] == 1
            assert data["search_query"] == "pasta recipe"
            assert len(data["recipes"]) == 1

            recipe = data["recipes"][0]
            assert recipe["title"] == "Spaghetti Carbonara"
            assert recipe["description"] == "A classic Italian pasta dish"
            assert len(recipe["ingredients"]) == 4
            assert len(recipe["instructions"]) == 4
            assert recipe["metadata"]["prep_time"] == 15
            assert recipe["metadata"]["difficulty"] == "intermediate"
            assert recipe["source_url"] == "https://www.seriouseats.com/carbonara"

    @pytest.mark.asyncio
    async def test_search_recipes_with_dietary_restrictions(
        self, client: TestClient, mock_recipe_result: RecipeResult
    ) -> None:
        """Test recipe search with dietary restrictions."""
        with patch(
            "src.makemyrecipe.services.recipe_service.recipe_service.search_recipes"
        ) as mock_search:
            mock_search.return_value = ([mock_recipe_result], "Raw response")

            response = client.post(
                "/recipes/search",
                json={
                    "query": "healthy recipe",
                    "dietary_restrictions": ["vegetarian", "gluten_free"],
                    "ingredients": ["vegetables", "quinoa"],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 1

    def test_search_recipes_invalid_request(self, client: TestClient) -> None:
        """Test recipe search with invalid request."""
        response = client.post(
            "/recipes/search",
            json={
                "query": "",  # Empty query should still work
                "cuisine": "invalid_cuisine",  # This should cause validation error
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_ingredient_suggestions_success(
        self, client: TestClient, mock_recipe_result: RecipeResult
    ) -> None:
        """Test ingredient-based recipe suggestions."""
        with patch(
            "src.makemyrecipe.services.recipe_service.recipe_service.get_recipe_suggestions"
        ) as mock_suggestions:
            mock_suggestions.return_value = ([mock_recipe_result], "Raw response")

            response = client.post(
                "/recipes/suggestions/ingredients",
                json={
                    "ingredients": ["chicken", "rice", "vegetables"],
                    "dietary_restrictions": ["gluten_free"],
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert data["total_count"] == 1
            assert "chicken, rice, vegetables" in data["search_query"]
            assert len(data["recipes"]) == 1

    def test_ingredient_suggestions_empty_ingredients(self, client: TestClient) -> None:
        """Test ingredient suggestions with empty ingredients list."""
        response = client.post(
            "/recipes/suggestions/ingredients", json={"ingredients": []}
        )

        assert response.status_code == 422  # Should require at least one ingredient

    @pytest.mark.asyncio
    async def test_cuisine_recipes_success(
        self, client: TestClient, mock_recipe_result: RecipeResult
    ) -> None:
        """Test cuisine-specific recipe search."""
        with patch(
            "src.makemyrecipe.services.recipe_service.recipe_service.get_cuisine_recipes"
        ) as mock_cuisine:
            mock_cuisine.return_value = ([mock_recipe_result], "Raw response")

            response = client.post(
                "/recipes/cuisine",
                json={"cuisine": "italian", "difficulty": "beginner"},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["total_count"] == 1
            assert "italian recipes" in data["search_query"]
            assert "beginner level" in data["search_query"]

    def test_cuisine_recipes_invalid_cuisine(self, client: TestClient) -> None:
        """Test cuisine recipes with invalid cuisine."""
        response = client.post("/recipes/cuisine", json={"cuisine": "invalid_cuisine"})

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_quick_search_success(
        self, client: TestClient, mock_recipe_result: RecipeResult
    ) -> None:
        """Test quick recipe search with URL parameters."""
        with patch(
            "src.makemyrecipe.services.recipe_service.recipe_service.search_recipes"
        ) as mock_search:
            mock_search.return_value = ([mock_recipe_result], "Raw response")

            response = client.get(
                "/recipes/quick-search",
                params={
                    "q": "pasta recipe",
                    "cuisine": "italian",
                    "difficulty": "intermediate",
                    "max_time": 45,
                    "dietary": ["vegetarian"],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 1

    def test_quick_search_missing_query(self, client: TestClient) -> None:
        """Test quick search without required query parameter."""
        response = client.get("/recipes/quick-search")

        assert response.status_code == 422  # Missing required parameter

    def test_get_supported_cuisines(self, client: TestClient) -> None:
        """Test getting supported cuisine types."""
        response = client.get("/recipes/cuisines")

        assert response.status_code == 200
        cuisines = response.json()

        assert isinstance(cuisines, list)
        assert len(cuisines) > 0
        assert "italian" in cuisines
        assert "chinese" in cuisines
        assert "mexican" in cuisines

    def test_get_supported_dietary_restrictions(self, client: TestClient) -> None:
        """Test getting supported dietary restrictions."""
        response = client.get("/recipes/dietary-restrictions")

        assert response.status_code == 200
        restrictions = response.json()

        assert isinstance(restrictions, list)
        assert len(restrictions) > 0
        assert "vegetarian" in restrictions
        assert "vegan" in restrictions
        assert "gluten_free" in restrictions

    def test_get_difficulty_levels(self, client: TestClient) -> None:
        """Test getting difficulty levels."""
        response = client.get("/recipes/difficulty-levels")

        assert response.status_code == 200
        levels = response.json()

        assert isinstance(levels, list)
        assert len(levels) == 3
        assert "beginner" in levels
        assert "intermediate" in levels
        assert "advanced" in levels

    def test_get_trusted_domains(self, client: TestClient) -> None:
        """Test getting trusted recipe domains."""
        response = client.get("/recipes/trusted-domains")

        assert response.status_code == 200
        domains = response.json()

        assert isinstance(domains, list)
        assert len(domains) > 0
        assert "allrecipes.com" in domains
        assert "foodnetwork.com" in domains
        assert "seriouseats.com" in domains

    def test_recipe_service_health(self, client: TestClient) -> None:
        """Test recipe service health check."""
        response = client.get("/recipes/health")

        assert response.status_code == 200
        health = response.json()

        assert health["status"] == "healthy"
        assert health["service"] == "recipe_service"
        assert "trusted_domains_count" in health
        assert "supported_cuisines" in health
        assert "supported_dietary_restrictions" in health

    @pytest.mark.asyncio
    async def test_search_recipes_service_error(self, client: TestClient) -> None:
        """Test recipe search when service throws an error."""
        with patch(
            "src.makemyrecipe.services.recipe_service.recipe_service.search_recipes"
        ) as mock_search:
            mock_search.side_effect = Exception("Service unavailable")

            response = client.post("/recipes/search", json={"query": "pasta recipe"})

            assert response.status_code == 500
            data = response.json()
            assert "Recipe search failed" in data["detail"]

    @pytest.mark.asyncio
    async def test_ingredient_suggestions_service_error(
        self, client: TestClient
    ) -> None:
        """Test ingredient suggestions when service throws an error."""
        with patch(
            "src.makemyrecipe.services.recipe_service.recipe_service.get_recipe_suggestions"
        ) as mock_suggestions:
            mock_suggestions.side_effect = Exception("Service unavailable")

            response = client.post(
                "/recipes/suggestions/ingredients",
                json={"ingredients": ["chicken", "rice"]},
            )

            assert response.status_code == 500
            data = response.json()
            assert "Ingredient suggestions failed" in data["detail"]

    @pytest.mark.asyncio
    async def test_cuisine_recipes_service_error(self, client: TestClient) -> None:
        """Test cuisine recipes when service throws an error."""
        with patch(
            "src.makemyrecipe.services.recipe_service.recipe_service.get_cuisine_recipes"
        ) as mock_cuisine:
            mock_cuisine.side_effect = Exception("Service unavailable")

            response = client.post("/recipes/cuisine", json={"cuisine": "italian"})

            assert response.status_code == 500
            data = response.json()
            assert "Cuisine recipes failed" in data["detail"]

    def test_recipe_search_request_validation(self, client: TestClient) -> None:
        """Test recipe search request validation."""
        # Test with valid minimal request
        response = client.post("/recipes/search", json={"query": "simple pasta"})
        # Should not fail validation (might fail at service level, but that's different)
        assert response.status_code != 422

        # Test with all valid fields
        response = client.post(
            "/recipes/search",
            json={
                "query": "healthy dinner",
                "ingredients": ["chicken", "vegetables"],
                "exclude_ingredients": ["nuts"],
                "cuisine": "mediterranean",
                "dietary_restrictions": ["gluten_free"],
                "difficulty": "intermediate",
                "max_prep_time": 30,
                "max_cook_time": 45,
                "servings": 4,
                "recipe_type": "main course",
            },
        )
        assert response.status_code != 422

    def test_ingredient_suggestion_request_validation(self, client: TestClient) -> None:
        """Test ingredient suggestion request validation."""
        # Test with valid request
        response = client.post(
            "/recipes/suggestions/ingredients",
            json={
                "ingredients": ["tomatoes", "basil", "mozzarella"],
                "dietary_restrictions": ["vegetarian"],
            },
        )
        assert response.status_code != 422

        # Test with minimal valid request
        response = client.post(
            "/recipes/suggestions/ingredients", json={"ingredients": ["eggs"]}
        )
        assert response.status_code != 422

    def test_cuisine_recipe_request_validation(self, client: TestClient) -> None:
        """Test cuisine recipe request validation."""
        # Test with valid minimal request
        response = client.post("/recipes/cuisine", json={"cuisine": "thai"})
        assert response.status_code != 422

        # Test with difficulty specified
        response = client.post(
            "/recipes/cuisine", json={"cuisine": "french", "difficulty": "advanced"}
        )
        assert response.status_code != 422
