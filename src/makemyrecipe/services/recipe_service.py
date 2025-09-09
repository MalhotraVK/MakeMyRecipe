"""Recipe recommendation engine using Claude web search capabilities."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..core.config import settings
from ..core.logging import get_logger
from ..models.chat import ChatMessage
from .anthropic_service import anthropic_service

logger = get_logger(__name__)


class DifficultyLevel(str, Enum):
    """Recipe difficulty levels."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class CuisineType(str, Enum):
    """Supported cuisine types."""

    ITALIAN = "italian"
    CHINESE = "chinese"
    MEXICAN = "mexican"
    INDIAN = "indian"
    FRENCH = "french"
    JAPANESE = "japanese"
    THAI = "thai"
    MEDITERRANEAN = "mediterranean"
    AMERICAN = "american"
    MIDDLE_EASTERN = "middle_eastern"
    KOREAN = "korean"
    VIETNAMESE = "vietnamese"


class DietaryRestriction(str, Enum):
    """Supported dietary restrictions."""

    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    KETO = "keto"
    PALEO = "paleo"
    LOW_CARB = "low_carb"
    LOW_SODIUM = "low_sodium"
    DIABETIC = "diabetic"


@dataclass
class RecipeMetadata:
    """Recipe metadata extracted from search results."""

    prep_time: Optional[int] = None  # minutes
    cook_time: Optional[int] = None  # minutes
    total_time: Optional[int] = None  # minutes
    servings: Optional[int] = None
    difficulty: Optional[DifficultyLevel] = None
    cuisine: Optional[CuisineType] = None
    dietary_restrictions: List[DietaryRestriction] = field(default_factory=list)
    calories_per_serving: Optional[int] = None


@dataclass
class RecipeSearchQuery:
    """Recipe search query parameters."""

    ingredients: List[str] = field(default_factory=list)
    cuisine: Optional[CuisineType] = None
    dietary_restrictions: List[DietaryRestriction] = field(default_factory=list)
    difficulty: Optional[DifficultyLevel] = None
    max_prep_time: Optional[int] = None  # minutes
    max_cook_time: Optional[int] = None  # minutes
    servings: Optional[int] = None
    exclude_ingredients: List[str] = field(default_factory=list)
    recipe_type: Optional[str] = None  # e.g., "dessert", "main course", "appetizer"


@dataclass
class RecipeResult:
    """Structured recipe result."""

    title: str
    description: str
    ingredients: List[str]
    instructions: List[str]
    metadata: RecipeMetadata
    source_url: str
    source_name: str
    rating: Optional[float] = None
    review_count: Optional[int] = None


class RecipeService:
    """Service for recipe recommendations using Claude web search."""

    # Trusted recipe domains for domain filtering
    TRUSTED_DOMAINS = [
        "allrecipes.com",
        "foodnetwork.com",
        "seriouseats.com",
        "bonappetit.com",
        "epicurious.com",
        "tasteofhome.com",
        "delish.com",
        "food.com",
        "myrecipes.com",
        "cookinglight.com",
        "eatingwell.com",
        "simplyrecipes.com",
        "thekitchn.com",
        "recipetineats.com",
        "minimalistbaker.com",
        "budgetbytes.com",
        "skinnytaste.com",
        "kingarthurbaking.com",
        "americastestkitchen.com",
        "cooksillustrated.com",
    ]

    def __init__(self) -> None:
        """Initialize the recipe service."""
        self.anthropic_service = anthropic_service

    def _create_domain_filter_string(self) -> str:
        """Create domain filter string for search queries."""
        return " OR ".join([f"site:{domain}" for domain in self.TRUSTED_DOMAINS])

    def _build_search_query(self, query: RecipeSearchQuery, user_query: str) -> str:
        """Build optimized search query for recipe recommendations."""
        query_parts = []

        # Add the user's original query
        if user_query:
            query_parts.append(user_query)

        # Add ingredients if specified
        if query.ingredients:
            ingredients_str = " ".join(query.ingredients)
            query_parts.append(f"recipe with {ingredients_str}")

        # Add cuisine type
        if query.cuisine:
            query_parts.append(f"{query.cuisine.value} cuisine")

        # Add dietary restrictions
        if query.dietary_restrictions:
            for restriction in query.dietary_restrictions:
                query_parts.append(restriction.value.replace("_", " "))

        # Add recipe type
        if query.recipe_type:
            query_parts.append(query.recipe_type)

        # Add time constraints
        if query.max_prep_time:
            query_parts.append(f"quick {query.max_prep_time} minutes")

        # Add difficulty
        if query.difficulty:
            query_parts.append(f"{query.difficulty.value} recipe")

        # Exclude ingredients
        if query.exclude_ingredients:
            for ingredient in query.exclude_ingredients:
                query_parts.append(f"-{ingredient}")

        # Combine query parts
        search_query = " ".join(query_parts)

        # Add domain filtering
        domain_filter = self._create_domain_filter_string()
        search_query = f"({search_query}) AND ({domain_filter})"

        return search_query

    def _create_recipe_prompt(self, query: RecipeSearchQuery, user_query: str) -> str:
        """Create optimized prompt for recipe generation."""
        prompt_parts = [
            "You are MakeMyRecipe, an expert culinary AI assistant. "
            "I need you to find and recommend high-quality recipes based on "
            "the following criteria:"
        ]

        if user_query:
            prompt_parts.append(f"\nUser Request: {user_query}")

        if query.ingredients:
            prompt_parts.append(
                f"\nIngredients to include: {', '.join(query.ingredients)}"
            )

        if query.exclude_ingredients:
            prompt_parts.append(
                f"\nIngredients to avoid: {', '.join(query.exclude_ingredients)}"
            )

        if query.cuisine:
            prompt_parts.append(f"\nCuisine type: {query.cuisine.value}")

        if query.dietary_restrictions:
            restrictions = [
                r.value.replace("_", " ") for r in query.dietary_restrictions
            ]
            prompt_parts.append(f"\nDietary restrictions: {', '.join(restrictions)}")

        if query.difficulty:
            prompt_parts.append(f"\nDifficulty level: {query.difficulty.value}")

        if query.max_prep_time:
            prompt_parts.append(
                f"\nMaximum preparation time: {query.max_prep_time} minutes"
            )

        if query.max_cook_time:
            prompt_parts.append(
                f"\nMaximum cooking time: {query.max_cook_time} minutes"
            )

        if query.servings:
            prompt_parts.append(f"\nNumber of servings: {query.servings}")

        if query.recipe_type:
            prompt_parts.append(f"\nRecipe type: {query.recipe_type}")

        prompt_parts.extend(
            [
                "\nPlease search for recipes that match these criteria and provide:",
                "1. Recipe title and brief description",
                "2. Complete ingredient list with measurements",
                "3. Step-by-step cooking instructions",
                "4. Preparation time, cooking time, and total time",
                "5. Number of servings",
                "6. Difficulty level (beginner/intermediate/advanced)",
                "7. Any relevant dietary information",
                "8. Source website and URL",
                "9. User ratings if available",
                "\nFocus on recipes from trusted cooking websites and prioritize "
                "those with good reviews.",
                "If multiple recipes match the criteria, provide 2-3 of the "
                "best options.",
            ]
        )

        return "\n".join(prompt_parts)

    def _extract_recipe_metadata(self, content: str) -> RecipeMetadata:
        """Extract recipe metadata from response content."""
        metadata = RecipeMetadata()

        # Extract time information with more flexible patterns
        time_patterns = [
            (r"prep(?:aration)?\s*time:?\s*(\d+)\s*(?:min|minutes?)", "prep_time"),
            (r"cook(?:ing)?\s*time:?\s*(\d+)\s*(?:min|minutes?)", "cook_time"),
            (r"total\s*time:?\s*(\d+)\s*(?:min|minutes?)", "total_time"),
            (r"\*\*prep\s*time:\*\*\s*(\d+)\s*(?:min|minutes?)", "prep_time"),
            (r"\*\*cook\s*time:\*\*\s*(\d+)\s*(?:min|minutes?)", "cook_time"),
            (r"\*\*total\s*time:\*\*\s*(\d+)\s*(?:min|minutes?)", "total_time"),
        ]

        for pattern, attr in time_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                setattr(metadata, attr, int(match.group(1)))

        # Extract servings with more patterns (most specific first)
        servings_patterns = [
            r"\*\*servings:\*\*\s*(\d+)",
            r"\*\*serv(?:es|ings?):\*\*\s*(\d+)",
            r"serves?\s+(\d+)",
            r"serv(?:es|ings?):?\s*(\d+)",
        ]

        for pattern in servings_patterns:
            servings_match = re.search(pattern, content, re.IGNORECASE)
            if servings_match:
                metadata.servings = int(servings_match.group(1))
                break

        # Extract difficulty with more patterns
        difficulty_patterns = [
            (r"\b(beginner|easy|simple)\b", DifficultyLevel.BEGINNER),
            (r"\b(intermediate|medium|moderate)\b", DifficultyLevel.INTERMEDIATE),
            (r"\b(advanced|hard|difficult|expert)\b", DifficultyLevel.ADVANCED),
            (r"\*\*difficulty:\*\*\s*(beginner|easy|simple)", DifficultyLevel.BEGINNER),
            (
                r"\*\*difficulty:\*\*\s*(intermediate|medium|moderate)",
                DifficultyLevel.INTERMEDIATE,
            ),
            (
                r"\*\*difficulty:\*\*\s*(advanced|hard|difficult|expert)",
                DifficultyLevel.ADVANCED,
            ),
        ]

        for pattern, difficulty in difficulty_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                metadata.difficulty = difficulty
                break

        # Extract cuisine type
        for cuisine in CuisineType:
            cuisine_text = cuisine.value.replace("_", " ")
            if cuisine_text in content.lower():
                metadata.cuisine = cuisine
                break

        # Extract dietary restrictions
        for restriction in DietaryRestriction:
            restriction_text = restriction.value.replace("_", " ")
            if restriction_text in content.lower():
                metadata.dietary_restrictions.append(restriction)

        # Extract calories with more patterns
        calories_patterns = [
            r"(\d+)\s*calories?",
            r"\*\*calories:\*\*\s*(\d+)",
            r"calories?:?\s*(\d+)",
        ]

        for pattern in calories_patterns:
            calories_match = re.search(pattern, content, re.IGNORECASE)
            if calories_match:
                metadata.calories_per_serving = int(calories_match.group(1))
                break

        return metadata

    def _parse_recipe_response(
        self, content: str, citations: List[Dict[str, Any]]
    ) -> List[RecipeResult]:
        """Parse recipe response into structured format."""
        recipes = []

        # Split content into recipe sections
        # This is a simplified parser - in production, you might want more
        # sophisticated parsing
        recipe_sections = re.split(r"\n(?=\d+\.\s|\*\*Recipe\s+\d+|\*\*\w+)", content)

        for i, section in enumerate(recipe_sections):
            if not section.strip():
                continue

            # Extract title
            title_match = re.search(r"\*\*([^*]+)\*\*|^([^\n]+)", section)
            title = (
                title_match.group(1) or title_match.group(2)
                if title_match
                else f"Recipe {i+1}"
            )
            title = title.strip()

            # Extract description
            description_lines = []
            lines = section.split("\n")
            for line in lines[1:6]:  # Take first few lines as description
                if line.strip() and not line.strip().startswith(
                    ("Ingredients:", "Instructions:", "Prep time:")
                ):
                    description_lines.append(line.strip())
            description = " ".join(description_lines)

            # Extract ingredients
            ingredients = []
            in_ingredients = False
            for line in lines:
                if "ingredients:" in line.lower():
                    in_ingredients = True
                    continue
                elif "instructions:" in line.lower() or "directions:" in line.lower():
                    in_ingredients = False
                elif in_ingredients and line.strip():
                    # Clean up ingredient line
                    ingredient = re.sub(r"^[-*•]\s*", "", line.strip())
                    if ingredient:
                        ingredients.append(ingredient)

            # Extract instructions
            instructions = []
            in_instructions = False
            for line in lines:
                if any(
                    word in line.lower()
                    for word in ["instructions:", "directions:", "method:"]
                ):
                    in_instructions = True
                    continue
                elif in_instructions and line.strip():
                    # Skip metadata lines that might be mixed in with instructions
                    if any(
                        word in line.lower()
                        for word in [
                            "prep time:",
                            "cook time:",
                            "total time:",
                            "servings:",
                            "difficulty:",
                            "calories:",
                        ]
                    ):
                        continue
                    # Clean up instruction line
                    instruction = re.sub(r"^\d+\.\s*", "", line.strip())
                    instruction = re.sub(
                        r"^\*\*.*?\*\*\s*", "", instruction
                    )  # Remove markdown formatting
                    if instruction:
                        instructions.append(instruction)

            # Extract metadata
            metadata = self._extract_recipe_metadata(section)

            # Find matching citation
            source_url = ""
            source_name = ""
            if citations and i < len(citations):
                citation = citations[i] if i < len(citations) else citations[0]
                source_url = citation.get("url", "")
                source_name = citation.get("title", "")

            # Create recipe result
            recipe = RecipeResult(
                title=title,
                description=description,
                ingredients=ingredients,
                instructions=instructions,
                metadata=metadata,
                source_url=source_url,
                source_name=source_name,
            )

            recipes.append(recipe)

        return recipes

    async def search_recipes(
        self, user_query: str, query_params: Optional[RecipeSearchQuery] = None
    ) -> Tuple[List[RecipeResult], str]:
        """
        Search for recipes based on user query and parameters.

        Returns:
            Tuple of (recipe_results, raw_response_content)
        """
        if query_params is None:
            query_params = RecipeSearchQuery()

        try:
            # Create optimized prompt
            prompt = self._create_recipe_prompt(query_params, user_query)

            # Create messages for the conversation
            messages = [ChatMessage(role="user", content=prompt)]

            # Generate response using Anthropic service with web search
            content, citations = await self.anthropic_service.generate_recipe_response(
                messages=messages,
                use_web_search=True,
            )

            # Parse response into structured recipes
            recipes = self._parse_recipe_response(content, citations)

            logger.info(f"Found {len(recipes)} recipes for query: {user_query}")

            return recipes, content

        except Exception as e:
            logger.error(f"Error searching recipes: {e}")
            return (
                [],
                f"Sorry, I encountered an error while searching for recipes: {str(e)}",
            )

    async def get_recipe_suggestions(
        self,
        ingredients: List[str],
        dietary_restrictions: Optional[List[DietaryRestriction]] = None,
    ) -> Tuple[List[RecipeResult], str]:
        """Get recipe suggestions based on available ingredients."""
        query_params = RecipeSearchQuery(
            ingredients=ingredients,
            dietary_restrictions=dietary_restrictions or [],
        )

        user_query = f"What can I make with {', '.join(ingredients)}?"

        return await self.search_recipes(user_query, query_params)

    async def get_cuisine_recipes(
        self, cuisine: CuisineType, difficulty: Optional[DifficultyLevel] = None
    ) -> Tuple[List[RecipeResult], str]:
        """Get recipes for a specific cuisine type."""
        query_params = RecipeSearchQuery(
            cuisine=cuisine,
            difficulty=difficulty,
        )

        user_query = f"Show me {cuisine.value} recipes"
        if difficulty:
            user_query += f" that are {difficulty.value} level"

        return await self.search_recipes(user_query, query_params)

    def optimize_search_query(self, original_query: str) -> str:
        """Optimize search query for better results and cost efficiency."""
        # Remove redundant words but keep important ones
        stop_words = [
            "the",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "i",
            "want",
        ]
        words = original_query.lower().split()
        filtered_words = [word for word in words if word not in stop_words]

        # Add recipe-specific terms if not present
        recipe_terms = ["recipe", "cook", "make", "prepare"]
        if not any(term in filtered_words for term in recipe_terms):
            filtered_words.append("recipe")

        return " ".join(filtered_words)


# Global recipe service instance
recipe_service = RecipeService()
