"""Integration tests for recipe recommendation engine."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.makemyrecipe.api.main import create_app
from src.makemyrecipe.services.recipe_service import (
    CuisineType,
    DietaryRestriction,
    DifficultyLevel,
)


class TestRecipeIntegration:
    """Integration tests for the complete recipe recommendation flow."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client for integration testing."""
        app = create_app()
        return TestClient(app)

    def test_app_includes_recipe_routes(self, client: TestClient) -> None:
        """Test that the app includes recipe routes."""
        # Test that recipe endpoints are available
        response = client.get("/recipes/health")
        assert response.status_code == 200

        response = client.get("/recipes/cuisines")
        assert response.status_code == 200

        response = client.get("/recipes/dietary-restrictions")
        assert response.status_code == 200

    def test_recipe_search_endpoint_integration(self, client: TestClient) -> None:
        """Test recipe search endpoint integration."""
        # Mock the Anthropic service to avoid actual API calls
        mock_response = """
        **Chicken Stir Fry**

        A quick and healthy Asian-inspired dish.

        **Ingredients:**
        - 500g chicken breast, sliced
        - 2 cups mixed vegetables
        - 2 tbsp soy sauce
        - 1 tbsp sesame oil

        **Instructions:**
        1. Heat oil in a wok
        2. Add chicken and cook until done
        3. Add vegetables and stir fry
        4. Season with soy sauce

        **Prep time:** 10 minutes
        **Cook time:** 15 minutes
        **Servings:** 4
        **Difficulty:** Beginner
        """

        mock_citations = [
            {
                "title": "Easy Chicken Stir Fry Recipe",
                "url": "https://www.allrecipes.com/chicken-stir-fry",
                "snippet": "Quick and easy stir fry recipe",
            }
        ]

        with patch(
            "src.makemyrecipe.services.anthropic_service.anthropic_service.generate_recipe_response"
        ) as mock_generate:
            mock_generate.return_value = (mock_response, mock_citations)

            response = client.post(
                "/recipes/search",
                json={
                    "query": "chicken stir fry",
                    "cuisine": "chinese",
                    "difficulty": "beginner",
                    "max_prep_time": 30,
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert data["total_count"] >= 1
            assert data["search_query"] == "chicken stir fry"

            if data["recipes"]:
                recipe = data["recipes"][0]
                assert "title" in recipe
                assert "ingredients" in recipe
                assert "instructions" in recipe
                assert "metadata" in recipe
                assert "source_url" in recipe

    def test_ingredient_suggestions_integration(self, client: TestClient) -> None:
        """Test ingredient suggestions endpoint integration."""
        mock_response = """
        **Tomato Basil Pasta**

        A simple vegetarian pasta dish.

        **Ingredients:**
        - 400g pasta
        - 4 large tomatoes
        - Fresh basil leaves
        - 2 cloves garlic
        - Olive oil

        **Instructions:**
        1. Cook pasta according to package directions
        2. Sauté garlic in olive oil
        3. Add chopped tomatoes
        4. Toss with pasta and basil

        **Prep time:** 5 minutes
        **Cook time:** 20 minutes
        **Servings:** 4
        **Difficulty:** Beginner
        """

        mock_citations = [
            {
                "title": "Simple Tomato Basil Pasta",
                "url": "https://www.foodnetwork.com/tomato-basil-pasta",
                "snippet": "Easy pasta with fresh ingredients",
            }
        ]

        with patch(
            "src.makemyrecipe.services.anthropic_service.anthropic_service.generate_recipe_response"
        ) as mock_generate:
            mock_generate.return_value = (mock_response, mock_citations)

            response = client.post(
                "/recipes/suggestions/ingredients",
                json={
                    "ingredients": ["tomatoes", "basil", "pasta"],
                    "dietary_restrictions": ["vegetarian"],
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert data["total_count"] >= 1
            assert "tomatoes, basil, pasta" in data["search_query"]

    def test_cuisine_recipes_integration(self, client: TestClient) -> None:
        """Test cuisine-specific recipes endpoint integration."""
        mock_response = """
        **Pad Thai**

        Classic Thai stir-fried noodle dish.

        **Ingredients:**
        - 200g rice noodles
        - 2 eggs
        - 100g tofu
        - Bean sprouts
        - Tamarind paste
        - Fish sauce
        - Palm sugar

        **Instructions:**
        1. Soak noodles in warm water
        2. Heat oil in wok
        3. Scramble eggs
        4. Add noodles and sauce
        5. Toss with vegetables

        **Prep time:** 15 minutes
        **Cook time:** 10 minutes
        **Servings:** 2
        **Difficulty:** Intermediate
        """

        mock_citations = [
            {
                "title": "Authentic Pad Thai Recipe",
                "url": "https://www.seriouseats.com/pad-thai-recipe",
                "snippet": "Traditional Thai noodle dish",
            }
        ]

        with patch(
            "src.makemyrecipe.services.anthropic_service.anthropic_service.generate_recipe_response"
        ) as mock_generate:
            mock_generate.return_value = (mock_response, mock_citations)

            response = client.post(
                "/recipes/cuisine",
                json={"cuisine": "thai", "difficulty": "intermediate"},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["total_count"] >= 1
            assert "thai recipes" in data["search_query"]
            assert "intermediate level" in data["search_query"]

    def test_quick_search_integration(self, client: TestClient) -> None:
        """Test quick search endpoint integration."""
        mock_response = """
        **Quick Omelette**

        A fast and easy breakfast dish.

        **Ingredients:**
        - 3 eggs
        - 2 tbsp milk
        - Salt and pepper
        - 1 tbsp butter

        **Instructions:**
        1. Beat eggs with milk
        2. Heat butter in pan
        3. Pour in eggs
        4. Fold when set

        **Prep time:** 2 minutes
        **Cook time:** 5 minutes
        **Servings:** 1
        **Difficulty:** Beginner
        """

        mock_citations = [
            {
                "title": "Perfect Omelette Recipe",
                "url": "https://www.tasteofhome.com/omelette-recipe",
                "snippet": "How to make a perfect omelette",
            }
        ]

        with patch(
            "src.makemyrecipe.services.anthropic_service.anthropic_service.generate_recipe_response"
        ) as mock_generate:
            mock_generate.return_value = (mock_response, mock_citations)

            response = client.get(
                "/recipes/quick-search",
                params={
                    "q": "quick breakfast",
                    "max_time": 10,
                    "difficulty": "beginner",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert data["search_query"] == "quick breakfast"

    def test_recipe_metadata_extraction_integration(self, client: TestClient) -> None:
        """Test that recipe metadata is properly extracted and returned."""
        mock_response = """
        **Beef Bourguignon**

        A classic French braised beef dish.

        **Ingredients:**
        - 2 lbs beef chuck
        - 1 bottle red wine
        - 8 oz bacon
        - Pearl onions
        - Mushrooms

        **Instructions:**
        1. Brown the beef in batches
        2. Sauté bacon and vegetables
        3. Add wine and herbs
        4. Braise for 2 hours

        **Prep time:** 30 minutes
        **Cook time:** 150 minutes
        **Total time:** 180 minutes
        **Servings:** 6
        **Difficulty:** Advanced
        **Calories:** 520 per serving
        """

        mock_citations = [
            {
                "title": "Classic Beef Bourguignon",
                "url": "https://www.bonappetit.com/beef-bourguignon",
                "snippet": "Traditional French beef stew",
            }
        ]

        with patch(
            "src.makemyrecipe.services.anthropic_service.anthropic_service.generate_recipe_response"
        ) as mock_generate:
            mock_generate.return_value = (mock_response, mock_citations)

            response = client.post(
                "/recipes/search",
                json={
                    "query": "beef bourguignon",
                    "cuisine": "french",
                    "difficulty": "advanced",
                },
            )

            assert response.status_code == 200
            data = response.json()

            if data["recipes"]:
                recipe = data["recipes"][0]
                metadata = recipe["metadata"]

                # Check that metadata was extracted correctly
                assert metadata["prep_time"] == 30
                assert metadata["cook_time"] == 150
                assert metadata["total_time"] == 180
                assert metadata["servings"] == 6
                assert metadata["difficulty"] == "advanced"
                assert metadata["calories_per_serving"] == 520

    def test_domain_filtering_integration(self, client: TestClient) -> None:
        """Test that domain filtering is applied in search queries."""
        with patch(
            "src.makemyrecipe.services.anthropic_service.anthropic_service.generate_recipe_response"
        ) as mock_generate:
            mock_generate.return_value = ("Mock response", [])

            response = client.post("/recipes/search", json={"query": "pasta recipe"})

            # Verify that the anthropic service was called
            mock_generate.assert_called_once()

            # The actual domain filtering logic is tested in unit tests
            # Here we just verify the integration works
            assert response.status_code == 200

    def test_error_handling_integration(self, client: TestClient) -> None:
        """Test error handling in the complete integration flow."""
        # Test when Anthropic service fails
        with patch(
            "src.makemyrecipe.services.recipe_service.recipe_service.search_recipes"
        ) as mock_search:
            mock_search.side_effect = Exception("API Error")

            response = client.post("/recipes/search", json={"query": "test recipe"})

            assert response.status_code == 500
            data = response.json()
            assert "Recipe search failed" in data["detail"]

    def test_recipe_service_health_integration(self, client: TestClient) -> None:
        """Test recipe service health check integration."""
        response = client.get("/recipes/health")

        assert response.status_code == 200
        health = response.json()

        assert health["status"] == "healthy"
        assert health["service"] == "recipe_service"
        assert isinstance(health["trusted_domains_count"], int)
        assert health["trusted_domains_count"] > 0
        assert isinstance(health["supported_cuisines"], int)
        assert isinstance(health["supported_dietary_restrictions"], int)

    def test_enum_endpoints_integration(self, client: TestClient) -> None:
        """Test that enum endpoints return correct values."""
        # Test cuisines
        response = client.get("/recipes/cuisines")
        assert response.status_code == 200
        cuisines = response.json()
        assert len(cuisines) == len(CuisineType)

        # Test dietary restrictions
        response = client.get("/recipes/dietary-restrictions")
        assert response.status_code == 200
        restrictions = response.json()
        assert len(restrictions) == len(DietaryRestriction)

        # Test difficulty levels
        response = client.get("/recipes/difficulty-levels")
        assert response.status_code == 200
        levels = response.json()
        assert len(levels) == len(DifficultyLevel)

    def test_trusted_domains_integration(self, client: TestClient) -> None:
        """Test trusted domains endpoint integration."""
        response = client.get("/recipes/trusted-domains")

        assert response.status_code == 200
        domains = response.json()

        assert isinstance(domains, list)
        assert len(domains) > 0

        # Verify some expected domains are present
        expected_domains = ["allrecipes.com", "foodnetwork.com", "seriouseats.com"]
        for domain in expected_domains:
            assert domain in domains
