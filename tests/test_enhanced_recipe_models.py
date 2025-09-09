"""Tests for enhanced Recipe models with citation support."""

import pytest
from datetime import datetime
from unittest.mock import patch

from src.makemyrecipe.models.recipe import (
    Citation,
    Recipe,
    convert_recipe_result_to_recipe,
    convert_citations_to_recipe_citations,
)
from src.makemyrecipe.services.recipe_service import (
    RecipeResult,
    RecipeMetadata,
    DifficultyLevel,
    CuisineType,
    DietaryRestriction,
)

# Rebuild the Recipe model to resolve forward references
Recipe.model_rebuild()


class TestCitation:
    """Test cases for Citation model."""

    def test_citation_creation(self):
        """Test basic citation creation."""
        citation = Citation(
            title="Best Pasta Recipe",
            url="https://example.com/pasta",
            snippet="A delicious pasta recipe...",
            domain="example.com",
            published_date="2024-01-01"
        )
        
        assert citation.title == "Best Pasta Recipe"
        assert citation.url == "https://example.com/pasta"
        assert citation.snippet == "A delicious pasta recipe..."
        assert citation.domain == "example.com"
        assert citation.published_date == "2024-01-01"

    def test_citation_minimal(self):
        """Test citation with minimal required fields."""
        citation = Citation(
            title="Recipe Title",
            url="https://example.com"
        )
        
        assert citation.title == "Recipe Title"
        assert citation.url == "https://example.com"
        assert citation.snippet is None
        assert citation.domain is None
        assert citation.published_date is None


class TestRecipe:
    """Test cases for Recipe model."""

    @pytest.fixture
    def sample_citation(self):
        """Create a sample citation for testing."""
        return Citation(
            title="Allrecipes Pasta",
            url="https://allrecipes.com/pasta",
            domain="allrecipes.com"
        )

    @pytest.fixture
    def sample_recipe(self, sample_citation):
        """Create a sample recipe for testing."""
        return Recipe(
            title="Spaghetti Carbonara",
            description="Classic Italian pasta dish",
            ingredients=["400g spaghetti", "200g pancetta", "4 eggs", "100g parmesan"],
            instructions=["Boil pasta", "Cook pancetta", "Mix eggs and cheese", "Combine all"],
            prep_time=15,
            cook_time=20,
            total_time=35,
            servings=4,
            difficulty=DifficultyLevel.INTERMEDIATE,
            cuisine=CuisineType.ITALIAN,
            dietary_restrictions=[],
            calories_per_serving=450,
            primary_source=sample_citation,
            rating=4.5,
            review_count=1250,
            search_query="carbonara recipe"
        )

    def test_recipe_creation(self, sample_recipe):
        """Test basic recipe creation."""
        assert sample_recipe.title == "Spaghetti Carbonara"
        assert sample_recipe.description == "Classic Italian pasta dish"
        assert len(sample_recipe.ingredients) == 4
        assert len(sample_recipe.instructions) == 4
        assert sample_recipe.prep_time == 15
        assert sample_recipe.cook_time == 20
        assert sample_recipe.total_time == 35
        assert sample_recipe.servings == 4
        assert sample_recipe.difficulty == DifficultyLevel.INTERMEDIATE
        assert sample_recipe.cuisine == CuisineType.ITALIAN
        assert sample_recipe.calories_per_serving == 450
        assert sample_recipe.rating == 4.5
        assert sample_recipe.review_count == 1250
        assert sample_recipe.search_query == "carbonara recipe"
        assert not sample_recipe.is_saved

    def test_recipe_id_generation(self, sample_citation):
        """Test that recipe ID is automatically generated."""
        recipe1 = Recipe(
            title="Recipe 1",
            description="Description 1",
            ingredients=["ingredient1"],
            instructions=["instruction1"],
            primary_source=sample_citation
        )
        
        recipe2 = Recipe(
            title="Recipe 2",
            description="Description 2",
            ingredients=["ingredient2"],
            instructions=["instruction2"],
            primary_source=sample_citation
        )
        
        assert recipe1.id != recipe2.id
        assert len(recipe1.id) > 0
        assert len(recipe2.id) > 0

    def test_recipe_timestamps(self, sample_recipe):
        """Test that timestamps are automatically set."""
        assert isinstance(sample_recipe.created_at, datetime)
        assert isinstance(sample_recipe.updated_at, datetime)
        assert sample_recipe.created_at <= sample_recipe.updated_at

    def test_get_all_citations(self, sample_recipe):
        """Test getting all citations."""
        additional_citation = Citation(
            title="Food Network Carbonara",
            url="https://foodnetwork.com/carbonara"
        )
        sample_recipe.add_citation(additional_citation)
        
        all_citations = sample_recipe.get_all_citations()
        assert len(all_citations) == 2
        assert sample_recipe.primary_source in all_citations
        assert additional_citation in all_citations

    def test_add_citation(self, sample_recipe):
        """Test adding additional citations."""
        initial_count = len(sample_recipe.additional_sources)
        initial_updated_at = sample_recipe.updated_at
        
        new_citation = Citation(
            title="Serious Eats Carbonara",
            url="https://seriouseats.com/carbonara"
        )
        
        sample_recipe.add_citation(new_citation)
        
        assert len(sample_recipe.additional_sources) == initial_count + 1
        assert new_citation in sample_recipe.additional_sources
        assert sample_recipe.updated_at > initial_updated_at

    def test_add_duplicate_citation(self, sample_recipe):
        """Test that duplicate citations are not added."""
        citation = Citation(
            title="Duplicate Citation",
            url="https://example.com/duplicate"
        )
        
        sample_recipe.add_citation(citation)
        initial_count = len(sample_recipe.additional_sources)
        
        # Try to add the same citation again
        sample_recipe.add_citation(citation)
        
        assert len(sample_recipe.additional_sources) == initial_count

    def test_update_rating(self, sample_recipe):
        """Test updating recipe rating."""
        initial_updated_at = sample_recipe.updated_at
        
        sample_recipe.update_rating(4.8, 1500)
        
        assert sample_recipe.rating == 4.8
        assert sample_recipe.review_count == 1500
        assert sample_recipe.updated_at > initial_updated_at

    def test_update_rating_clamping(self, sample_recipe):
        """Test that rating is clamped between 1-5."""
        sample_recipe.update_rating(0.5)
        assert sample_recipe.rating == 1.0
        
        sample_recipe.update_rating(6.0)
        assert sample_recipe.rating == 5.0


class TestConversionFunctions:
    """Test cases for conversion functions."""

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
            dietary_restrictions=[DietaryRestriction.VEGETARIAN],
            calories_per_serving=450
        )
        
        return RecipeResult(
            title="Test Recipe",
            description="Test description",
            ingredients=["ingredient1", "ingredient2"],
            instructions=["step1", "step2"],
            metadata=metadata,
            source_url="https://example.com/recipe",
            source_name="Example Site",
            rating=4.5,
            review_count=100
        )

    def test_convert_recipe_result_to_recipe(self, sample_recipe_result):
        """Test converting RecipeResult to Recipe."""
        search_query = "test query"
        
        recipe = convert_recipe_result_to_recipe(sample_recipe_result, search_query)
        
        assert isinstance(recipe, Recipe)
        assert recipe.title == sample_recipe_result.title
        assert recipe.description == sample_recipe_result.description
        assert recipe.ingredients == sample_recipe_result.ingredients
        assert recipe.instructions == sample_recipe_result.instructions
        assert recipe.prep_time == sample_recipe_result.metadata.prep_time
        assert recipe.cook_time == sample_recipe_result.metadata.cook_time
        assert recipe.total_time == sample_recipe_result.metadata.total_time
        assert recipe.servings == sample_recipe_result.metadata.servings
        assert recipe.difficulty == sample_recipe_result.metadata.difficulty
        assert recipe.cuisine == sample_recipe_result.metadata.cuisine
        assert recipe.dietary_restrictions == sample_recipe_result.metadata.dietary_restrictions
        assert recipe.calories_per_serving == sample_recipe_result.metadata.calories_per_serving
        assert recipe.rating == sample_recipe_result.rating
        assert recipe.review_count == sample_recipe_result.review_count
        assert recipe.search_query == search_query
        
        # Check primary source
        assert recipe.primary_source.title == sample_recipe_result.source_name
        assert recipe.primary_source.url == sample_recipe_result.source_url
        assert recipe.primary_source.domain == "example.com"

    def test_convert_citations_to_recipe_citations(self):
        """Test converting citation dictionaries to Citation objects."""
        citation_dicts = [
            {
                "title": "Recipe 1",
                "url": "https://site1.com/recipe1",
                "snippet": "Great recipe..."
            },
            {
                "title": "Recipe 2",
                "url": "https://site2.com/recipe2",
                "snippet": "Another great recipe..."
            }
        ]
        
        citations = convert_citations_to_recipe_citations(citation_dicts)
        
        assert len(citations) == 2
        assert all(isinstance(c, Citation) for c in citations)
        
        assert citations[0].title == "Recipe 1"
        assert citations[0].url == "https://site1.com/recipe1"
        assert citations[0].snippet == "Great recipe..."
        assert citations[0].domain == "site1.com"
        
        assert citations[1].title == "Recipe 2"
        assert citations[1].url == "https://site2.com/recipe2"
        assert citations[1].snippet == "Another great recipe..."
        assert citations[1].domain == "site2.com"

    def test_convert_citations_empty_data(self):
        """Test converting citations with missing data."""
        citation_dicts = [
            {
                "title": "",
                "url": "",
                "snippet": None
            }
        ]
        
        citations = convert_citations_to_recipe_citations(citation_dicts)
        
        assert len(citations) == 1
        assert citations[0].title == "Unknown Source"  # Default fallback
        assert citations[0].url == ""
        assert citations[0].snippet is None
        assert citations[0].domain is None  # None domain from empty URL