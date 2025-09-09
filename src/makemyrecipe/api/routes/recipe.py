"""Recipe recommendation API routes."""

from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ...core.logging import get_logger
from ...models.recipe import (
    CuisineRecipeRequest,
    IngredientSuggestionRequest,
    RecipeSearchRequest,
    RecipeSearchResponse,
    convert_recipe_result_to_response,
    convert_search_request_to_query,
)
from ...services.recipe_service import (
    CuisineType,
    DietaryRestriction,
    DifficultyLevel,
    recipe_service,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.post("/search", response_model=RecipeSearchResponse)
async def search_recipes(request: RecipeSearchRequest) -> RecipeSearchResponse:
    """
    Search for recipes based on user query and filters.

    This endpoint provides comprehensive recipe search functionality with support for:
    - Natural language queries
    - Ingredient-based filtering
    - Cuisine and dietary restriction filters
    - Time and difficulty constraints
    - Domain filtering for trusted recipe sources
    """
    try:
        # Convert request to internal query format
        query_params = convert_search_request_to_query(request)

        # Search for recipes
        recipe_results, raw_response = await recipe_service.search_recipes(
            user_query=request.query,
            query_params=query_params,
        )

        # Convert results to response format
        recipe_responses = [
            convert_recipe_result_to_response(recipe) for recipe in recipe_results
        ]

        return RecipeSearchResponse(
            recipes=recipe_responses,
            total_count=len(recipe_responses),
            search_query=request.query,
            raw_response=raw_response,
        )

    except Exception as e:
        logger.error(f"Error in recipe search: {e}")
        raise HTTPException(status_code=500, detail=f"Recipe search failed: {str(e)}")


@router.post("/suggestions/ingredients", response_model=RecipeSearchResponse)
async def get_ingredient_suggestions(
    request: IngredientSuggestionRequest,
) -> RecipeSearchResponse:
    """
    Get recipe suggestions based on available ingredients.

    This endpoint helps users find recipes they can make with ingredients
    they have on hand.
    It supports dietary restrictions and provides recipes from trusted
    cooking websites.
    """
    try:
        # Get recipe suggestions
        recipe_results, raw_response = await recipe_service.get_recipe_suggestions(
            ingredients=request.ingredients,
            dietary_restrictions=request.dietary_restrictions,
        )

        # Convert results to response format
        recipe_responses = [
            convert_recipe_result_to_response(recipe) for recipe in recipe_results
        ]

        user_query = f"What can I make with {', '.join(request.ingredients)}?"

        return RecipeSearchResponse(
            recipes=recipe_responses,
            total_count=len(recipe_responses),
            search_query=user_query,
            raw_response=raw_response,
        )

    except Exception as e:
        logger.error(f"Error in ingredient suggestions: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ingredient suggestions failed: {str(e)}"
        )


@router.post("/cuisine", response_model=RecipeSearchResponse)
async def get_cuisine_recipes(request: CuisineRecipeRequest) -> RecipeSearchResponse:
    """
    Get recipes for a specific cuisine type.

    This endpoint provides curated recipes from specific cuisines with optional
    difficulty filtering. Perfect for exploring new cuisines or finding recipes
    that match your cooking skill level.
    """
    try:
        # Get cuisine-specific recipes
        recipe_results, raw_response = await recipe_service.get_cuisine_recipes(
            cuisine=request.cuisine,
            difficulty=request.difficulty,
        )

        # Convert results to response format
        recipe_responses = [
            convert_recipe_result_to_response(recipe) for recipe in recipe_results
        ]

        user_query = f"{request.cuisine.value} recipes"
        if request.difficulty:
            user_query += f" ({request.difficulty.value} level)"

        return RecipeSearchResponse(
            recipes=recipe_responses,
            total_count=len(recipe_responses),
            search_query=user_query,
            raw_response=raw_response,
        )

    except Exception as e:
        logger.error(f"Error in cuisine recipes: {e}")
        raise HTTPException(status_code=500, detail=f"Cuisine recipes failed: {str(e)}")


@router.get("/quick-search")
async def quick_recipe_search(
    q: str = Query(..., description="Recipe search query"),
    cuisine: CuisineType = Query(None, description="Cuisine type filter"),
    difficulty: DifficultyLevel = Query(None, description="Difficulty level filter"),
    max_time: int = Query(None, description="Maximum total time in minutes"),
    dietary: List[DietaryRestriction] = Query(None, description="Dietary restrictions"),
) -> RecipeSearchResponse:
    """
    Quick recipe search with URL parameters.

    This endpoint provides a simple way to search for recipes using URL parameters,
    making it easy to integrate with web applications and bookmarkable searches.
    """
    try:
        # Create search request from query parameters
        request = RecipeSearchRequest(
            query=q,
            cuisine=cuisine,
            difficulty=difficulty,
            max_cook_time=max_time,
            dietary_restrictions=dietary or [],
        )

        # Use the main search endpoint logic
        result: RecipeSearchResponse = await search_recipes(request)
        return result

    except Exception as e:
        logger.error(f"Error in quick recipe search: {e}")
        raise HTTPException(
            status_code=500, detail=f"Quick recipe search failed: {str(e)}"
        )


@router.get("/cuisines", response_model=List[str])
async def get_supported_cuisines() -> List[str]:
    """Get list of supported cuisine types."""
    return [cuisine.value for cuisine in CuisineType]


@router.get("/dietary-restrictions", response_model=List[str])
async def get_supported_dietary_restrictions() -> List[str]:
    """Get list of supported dietary restrictions."""
    return [restriction.value for restriction in DietaryRestriction]


@router.get("/difficulty-levels", response_model=List[str])
async def get_difficulty_levels() -> List[str]:
    """Get list of supported difficulty levels."""
    return [level.value for level in DifficultyLevel]


@router.get("/trusted-domains", response_model=List[str])
async def get_trusted_domains() -> List[str]:
    """Get list of trusted recipe domains used for filtering."""
    return recipe_service.TRUSTED_DOMAINS


@router.get("/health")
async def recipe_service_health() -> JSONResponse:
    """Health check endpoint for recipe service."""
    try:
        # Basic health check - could be expanded to check Anthropic API connectivity
        return JSONResponse(
            content={
                "status": "healthy",
                "service": "recipe_service",
                "trusted_domains_count": len(recipe_service.TRUSTED_DOMAINS),
                "supported_cuisines": len(CuisineType),
                "supported_dietary_restrictions": len(DietaryRestriction),
            }
        )
    except Exception as e:
        logger.error(f"Recipe service health check failed: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503,
        )
