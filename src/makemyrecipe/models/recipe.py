"""Recipe-related data models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from ..services.recipe_service import (
    CuisineType,
    DietaryRestriction,
    DifficultyLevel,
    RecipeMetadata,
    RecipeResult,
    RecipeSearchQuery,
)


class RecipeSearchRequest(BaseModel):
    """Request model for recipe search."""

    query: str = Field(..., description="User's recipe search query")
    ingredients: Optional[List[str]] = Field(None, description="Ingredients to include")
    exclude_ingredients: Optional[List[str]] = Field(
        None, description="Ingredients to exclude"
    )
    cuisine: Optional[CuisineType] = Field(None, description="Cuisine type")
    dietary_restrictions: Optional[List[DietaryRestriction]] = Field(
        None, description="Dietary restrictions"
    )
    difficulty: Optional[DifficultyLevel] = Field(
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
    difficulty: Optional[DifficultyLevel] = Field(
        None, description="Recipe difficulty level"
    )
    cuisine: Optional[CuisineType] = Field(None, description="Cuisine type")
    dietary_restrictions: List[DietaryRestriction] = Field(
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
    dietary_restrictions: Optional[List[DietaryRestriction]] = Field(
        None, description="Dietary restrictions"
    )


class CuisineRecipeRequest(BaseModel):
    """Request model for cuisine-specific recipes."""

    cuisine: CuisineType = Field(..., description="Cuisine type")
    difficulty: Optional[DifficultyLevel] = Field(
        None, description="Recipe difficulty level"
    )


class RecipeRecommendationContext(BaseModel):
    """Context for recipe recommendations based on user history."""

    user_id: str = Field(..., description="User ID")
    preferred_cuisines: List[CuisineType] = Field(
        default_factory=list, description="User's preferred cuisines"
    )
    dietary_restrictions: List[DietaryRestriction] = Field(
        default_factory=list, description="User's dietary restrictions"
    )
    cooking_skill_level: Optional[DifficultyLevel] = Field(
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


def convert_recipe_result_to_response(recipe_result: RecipeResult) -> RecipeResponse:
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


def convert_search_request_to_query(request: RecipeSearchRequest) -> RecipeSearchQuery:
    """Convert RecipeSearchRequest to RecipeSearchQuery."""
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
