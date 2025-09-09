"""Recipe-related data models."""

from datetime import datetime, timezone

# Import types at runtime to avoid circular imports
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ..services.recipe_service import (
        CuisineType,
        DietaryRestriction,
        DifficultyLevel,
        RecipeMetadata,
        RecipeResult,
        RecipeSearchQuery,
    )


class Citation(BaseModel):
    """Citation model for recipe sources."""

    title: str = Field(..., description="Title of the source")
    url: str = Field(..., description="URL of the source")
    snippet: Optional[str] = Field(None, description="Brief excerpt from the source")
    domain: Optional[str] = Field(None, description="Domain of the source website")
    published_date: Optional[str] = Field(
        None, description="Publication date if available"
    )


class Recipe(BaseModel):
    """Enhanced Recipe model with comprehensive citation support."""

    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique recipe identifier"
    )
    title: str = Field(..., description="Recipe title")
    description: str = Field(..., description="Recipe description")
    ingredients: List[str] = Field(
        ..., description="List of ingredients with measurements"
    )
    instructions: List[str] = Field(
        ..., description="Step-by-step cooking instructions"
    )

    # Metadata
    prep_time: Optional[int] = Field(None, description="Preparation time in minutes")
    cook_time: Optional[int] = Field(None, description="Cooking time in minutes")
    total_time: Optional[int] = Field(None, description="Total time in minutes")
    servings: Optional[int] = Field(None, description="Number of servings")
    difficulty: Optional["DifficultyLevel"] = Field(
        None, description="Recipe difficulty level"
    )
    cuisine: Optional["CuisineType"] = Field(None, description="Cuisine type")
    dietary_restrictions: List["DietaryRestriction"] = Field(
        default_factory=list, description="Dietary restrictions"
    )
    calories_per_serving: Optional[int] = Field(
        None, description="Calories per serving"
    )

    # Source and citation information
    primary_source: Citation = Field(..., description="Primary source citation")
    additional_sources: List[Citation] = Field(
        default_factory=list, description="Additional source citations"
    )

    # User interaction
    rating: Optional[float] = Field(None, description="Recipe rating (1-5)")
    review_count: Optional[int] = Field(None, description="Number of reviews")
    user_notes: Optional[str] = Field(None, description="User's personal notes")
    is_saved: bool = Field(False, description="Whether user has saved this recipe")

    # System metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )
    search_query: Optional[str] = Field(
        None, description="Original search query that found this recipe"
    )

    def get_all_citations(self) -> List[Citation]:
        """Get all citations for this recipe."""
        return [self.primary_source] + self.additional_sources

    def add_citation(self, citation: Citation) -> None:
        """Add an additional citation to this recipe."""
        if citation not in self.additional_sources:
            self.additional_sources.append(citation)
            self.updated_at = datetime.now(timezone.utc)

    def update_rating(self, rating: float, review_count: Optional[int] = None) -> None:
        """Update recipe rating."""
        self.rating = max(1.0, min(5.0, rating))  # Clamp between 1-5
        if review_count is not None:
            self.review_count = review_count
        self.updated_at = datetime.now(timezone.utc)


class RecipeSearchRequest(BaseModel):
    """Request model for recipe search."""

    query: str = Field(..., description="User's recipe search query")
    ingredients: Optional[List[str]] = Field(None, description="Ingredients to include")
    exclude_ingredients: Optional[List[str]] = Field(
        None, description="Ingredients to exclude"
    )
    cuisine: Optional["CuisineType"] = Field(None, description="Cuisine type")
    dietary_restrictions: Optional[List["DietaryRestriction"]] = Field(
        None, description="Dietary restrictions"
    )
    difficulty: Optional["DifficultyLevel"] = Field(
        None, description="Recipe difficulty level"
    )
    max_prep_time: Optional[int] = Field(
        None, description="Maximum preparation time in minutes"
    )
    max_cook_time: Optional[int] = Field(
        None, description="Maximum cooking time in minutes"
    )
    servings: Optional[int] = Field(None, description="Number of servings")
    recipe_type: Optional[str] = Field(
        None, description="Type of recipe (e.g., dessert, main course)"
    )


class RecipeMetadataResponse(BaseModel):
    """Response model for recipe metadata."""

    prep_time: Optional[int] = Field(None, description="Preparation time in minutes")
    cook_time: Optional[int] = Field(None, description="Cooking time in minutes")
    total_time: Optional[int] = Field(None, description="Total time in minutes")
    servings: Optional[int] = Field(None, description="Number of servings")
    difficulty: Optional["DifficultyLevel"] = Field(
        None, description="Recipe difficulty level"
    )
    cuisine: Optional["CuisineType"] = Field(None, description="Cuisine type")
    dietary_restrictions: List["DietaryRestriction"] = Field(
        default_factory=list, description="Dietary restrictions"
    )
    calories_per_serving: Optional[int] = Field(
        None, description="Calories per serving"
    )


class RecipeResponse(BaseModel):
    """Response model for a single recipe."""

    title: str = Field(..., description="Recipe title")
    description: str = Field(..., description="Recipe description")
    ingredients: List[str] = Field(
        ..., description="List of ingredients with measurements"
    )
    instructions: List[str] = Field(
        ..., description="Step-by-step cooking instructions"
    )
    metadata: RecipeMetadataResponse = Field(..., description="Recipe metadata")
    source_url: str = Field(..., description="Source URL")
    source_name: str = Field(..., description="Source website name")
    rating: Optional[float] = Field(None, description="Recipe rating")
    review_count: Optional[int] = Field(None, description="Number of reviews")


class RecipeSearchResponse(BaseModel):
    """Response model for recipe search results."""

    recipes: List[RecipeResponse] = Field(..., description="List of found recipes")
    total_count: int = Field(..., description="Total number of recipes found")
    search_query: str = Field(..., description="Original search query")
    raw_response: Optional[str] = Field(
        None, description="Raw AI response for debugging"
    )


class IngredientSuggestionRequest(BaseModel):
    """Request model for ingredient-based recipe suggestions."""

    ingredients: List[str] = Field(
        ..., min_length=1, description="Available ingredients (at least one required)"
    )
    dietary_restrictions: Optional[List["DietaryRestriction"]] = Field(
        None, description="Dietary restrictions"
    )


class CuisineRecipeRequest(BaseModel):
    """Request model for cuisine-specific recipes."""

    cuisine: "CuisineType" = Field(..., description="Cuisine type")
    difficulty: Optional["DifficultyLevel"] = Field(
        None, description="Recipe difficulty level"
    )


class RecipeRecommendationContext(BaseModel):
    """Context for recipe recommendations based on user history."""

    user_id: str = Field(..., description="User ID")
    preferred_cuisines: List["CuisineType"] = Field(
        default_factory=list, description="User's preferred cuisines"
    )
    dietary_restrictions: List["DietaryRestriction"] = Field(
        default_factory=list, description="User's dietary restrictions"
    )
    cooking_skill_level: Optional["DifficultyLevel"] = Field(
        None, description="User's cooking skill level"
    )
    favorite_ingredients: List[str] = Field(
        default_factory=list, description="User's favorite ingredients"
    )
    disliked_ingredients: List[str] = Field(
        default_factory=list, description="User's disliked ingredients"
    )
    time_constraints: Optional[int] = Field(
        None, description="Typical cooking time preference in minutes"
    )


def convert_recipe_result_to_response(recipe_result: "RecipeResult") -> RecipeResponse:
    """Convert RecipeResult to RecipeResponse."""
    metadata_response = RecipeMetadataResponse(
        prep_time=recipe_result.metadata.prep_time,
        cook_time=recipe_result.metadata.cook_time,
        total_time=recipe_result.metadata.total_time,
        servings=recipe_result.metadata.servings,
        difficulty=recipe_result.metadata.difficulty,
        cuisine=recipe_result.metadata.cuisine,
        dietary_restrictions=recipe_result.metadata.dietary_restrictions,
        calories_per_serving=recipe_result.metadata.calories_per_serving,
    )

    return RecipeResponse(
        title=recipe_result.title,
        description=recipe_result.description,
        ingredients=recipe_result.ingredients,
        instructions=recipe_result.instructions,
        metadata=metadata_response,
        source_url=recipe_result.source_url,
        source_name=recipe_result.source_name,
        rating=recipe_result.rating,
        review_count=recipe_result.review_count,
    )


def convert_search_request_to_query(
    request: RecipeSearchRequest,
) -> "RecipeSearchQuery":
    """Convert RecipeSearchRequest to RecipeSearchQuery."""
    from ..services.recipe_service import RecipeSearchQuery

    return RecipeSearchQuery(
        ingredients=request.ingredients or [],
        cuisine=request.cuisine,
        dietary_restrictions=request.dietary_restrictions or [],
        difficulty=request.difficulty,
        max_prep_time=request.max_prep_time,
        max_cook_time=request.max_cook_time,
        servings=request.servings,
        exclude_ingredients=request.exclude_ingredients or [],
        recipe_type=request.recipe_type,
    )


def convert_recipe_result_to_recipe(
    recipe_result: "RecipeResult", search_query: Optional[str] = None
) -> Recipe:
    """Convert RecipeResult to enhanced Recipe model."""
    from urllib.parse import urlparse

    # Import types and rebuild model if needed
    try:
        from ..services.recipe_service import (
            CuisineType,
            DietaryRestriction,
            DifficultyLevel,
        )

        Recipe.model_rebuild()
    except Exception:
        pass  # Model may already be rebuilt

    # Create primary citation
    domain = (
        urlparse(recipe_result.source_url).netloc if recipe_result.source_url else None
    )
    primary_source = Citation(
        title=recipe_result.source_name or "Unknown Source",
        url=recipe_result.source_url or "",
        domain=domain,
    )

    return Recipe(
        title=recipe_result.title,
        description=recipe_result.description,
        ingredients=recipe_result.ingredients,
        instructions=recipe_result.instructions,
        prep_time=recipe_result.metadata.prep_time,
        cook_time=recipe_result.metadata.cook_time,
        total_time=recipe_result.metadata.total_time,
        servings=recipe_result.metadata.servings,
        difficulty=recipe_result.metadata.difficulty,
        cuisine=recipe_result.metadata.cuisine,
        dietary_restrictions=recipe_result.metadata.dietary_restrictions,
        calories_per_serving=recipe_result.metadata.calories_per_serving,
        primary_source=primary_source,
        rating=recipe_result.rating,
        review_count=recipe_result.review_count,
        search_query=search_query,
    )


def convert_citations_to_recipe_citations(
    citations: List[Dict[str, Any]],
) -> List[Citation]:
    """Convert citation dictionaries to Citation objects."""
    from urllib.parse import urlparse

    recipe_citations = []
    for citation_data in citations:
        title = citation_data.get("title", "")
        if not title or title.strip() == "":
            title = "Unknown Source"

        url = citation_data.get("url", "")
        domain = urlparse(url).netloc if url else None

        citation = Citation(
            title=title,
            url=url,
            snippet=citation_data.get("snippet"),
            domain=domain,
        )
        recipe_citations.append(citation)

    return recipe_citations


class EnhancedRecipeSearchResponse(BaseModel):
    """Response model for enhanced recipe search with full Recipe objects."""

    recipes: List[Recipe] = Field(..., description="List of found recipes")
    total_count: int = Field(..., description="Total number of recipes found")
    search_query: str = Field(..., description="Original search query")
    raw_response: Optional[str] = Field(None, description="Raw LLM response")
