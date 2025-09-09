"""LLM service for generating chat responses."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

from ..core.config import settings
from ..core.logging import get_logger
from ..models.chat import ChatMessage

if TYPE_CHECKING:
    import litellm
else:
    try:
        import litellm
    except ImportError:
        litellm = None  # type: ignore

# For mypy compatibility
litellm_module: Any = litellm

logger = get_logger(__name__)


class LLMService:
    """Service for generating LLM responses."""

    def __init__(self) -> None:
        """Initialize the LLM service."""
        self.model = settings.litellm_model
        self._setup_api_keys()

        # Import Anthropic service here to avoid circular imports
        from .anthropic_service import anthropic_service

        self.anthropic_service = anthropic_service

    def _setup_api_keys(self) -> None:
        """Set up API keys for LiteLLM."""
        if settings.openai_api_key:
            import os

            os.environ["OPENAI_API_KEY"] = settings.openai_api_key

        if settings.anthropic_api_key:
            import os

            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

    async def generate_response(
        self, messages: List[ChatMessage], system_prompt: Optional[str] = None
    ) -> str:
        """Generate a response using the LLM."""
        # Check if this is a recipe-related query and use Anthropic with web search
        if self._is_recipe_query(messages) and settings.anthropic_api_key:
            try:
                (
                    response,
                    citations,
                ) = await self.anthropic_service.generate_recipe_response(
                    messages,
                    system_prompt,
                    use_web_search=settings.anthropic_enable_web_search,
                )
                return response
            except Exception as e:
                logger.error(f"Anthropic service failed, falling back to LiteLLM: {e}")

        # Fallback to LiteLLM or mock response
        if litellm_module is None:
            logger.warning("LiteLLM not available, returning mock response")
            return self._get_mock_response(messages)

        # If we reach here, try LiteLLM
        try:
            # Convert messages to LiteLLM format
            llm_messages = []
            if system_prompt:
                llm_messages.append({"role": "system", "content": system_prompt})

            for msg in messages:
                llm_messages.append({"role": msg.role, "content": msg.content})

            # Generate response
            response = await litellm_module.acompletion(
                model=self.model,
                messages=llm_messages,
                temperature=0.7,
                max_tokens=1000,
            )

            content = getattr(response.choices[0].message, "content", None)  # noqa
            return (
                str(content)
                if content is not None
                else self._get_mock_response(messages)
            )

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return self._get_mock_response(messages)

    async def generate_response_with_citations(
        self, messages: List[ChatMessage], system_prompt: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Generate a response with citations using the LLM."""
        # Check if this is a recipe-related query and use Anthropic with web search
        if self._is_recipe_query(messages) and settings.anthropic_api_key:
            try:
                return await self.anthropic_service.generate_recipe_response(
                    messages,
                    system_prompt,
                    use_web_search=settings.anthropic_enable_web_search,
                )
            except Exception as e:
                logger.error(f"Anthropic service failed, falling back to LiteLLM: {e}")

        # Fallback to regular response without citations
        response = await self.generate_response(messages, system_prompt)
        return response, []

    def _is_recipe_query(self, messages: List[ChatMessage]) -> bool:
        """Determine if the query is recipe-related."""
        if not messages:
            return False

        last_message = messages[-1].content.lower()
        recipe_keywords = [
            "recipe",
            "cook",
            "cooking",
            "bake",
            "baking",
            "make",
            "prepare",
            "ingredient",
            "ingredients",
            "dish",
            "meal",
            "food",
            "cuisine",
            "how to cook",
            "how to make",
            "how to bake",
            "dinner",
            "lunch",
            "breakfast",
            "dessert",
            "appetizer",
            "snack",
            "vegetarian",
            "vegan",
        ]

        return any(keyword in last_message for keyword in recipe_keywords)

    async def _generate_with_litellm(
        self, messages: List[ChatMessage], system_prompt: Optional[str] = None
    ) -> str:
        """Generate response using LiteLLM."""
        try:
            # Convert messages to LiteLLM format
            llm_messages = []

            # Add system prompt if provided
            if system_prompt:
                llm_messages.append({"role": "system", "content": system_prompt})

            # Add conversation messages
            for msg in messages:
                llm_messages.append({"role": msg.role, "content": msg.content})

            # Generate response
            response = await litellm_module.acompletion(
                model=self.model,
                messages=llm_messages,
                temperature=0.7,
                max_tokens=1000,
            )

            content = getattr(response.choices[0].message, "content", None)  # noqa
            return (
                str(content)
                if content is not None
                else self._get_mock_response(messages)
            )

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return self._get_mock_response(messages)

    def _get_mock_response(self, messages: List[ChatMessage]) -> str:
        """Generate a mock response when LLM is not available."""
        if not messages:
            return (
                "Hello! I'm MakeMyRecipe, your AI cooking assistant. "
                "How can I help you create something delicious today?"
            )

        last_message = messages[-1].content.lower()
        logger.info(f"Mock response for message: '{last_message}'")

        # Debug: Check each keyword individually
        pasta_keywords = ["pasta", "spaghetti", "noodles"]
        chicken_keywords = ["chicken", "poultry"]
        dessert_keywords = ["dessert", "sweet", "cake", "cookie"]

        logger.info(
            f"Pasta match: {any(word in last_message for word in pasta_keywords)}"
        )
        logger.info(
            f"Chicken match: {any(word in last_message for word in chicken_keywords)}"
        )
        logger.info(
            f"Dessert match: {any(word in last_message for word in dessert_keywords)}"
        )

        for word in dessert_keywords:
            if word in last_message:
                logger.info(
                    f"Found dessert keyword: '{word}' in message: '{last_message}'"
                )

        # Simple keyword-based responses with proper markdown formatting
        if any(word in last_message for word in ["pasta", "spaghetti", "noodles"]):
            logger.info("Matched pasta keywords")
            return (
                "I'd love to help you make pasta! Here's a simple and "
                "delicious recipe:\n\n"
                "## Classic Tomato Pasta\n\n"
                "### Ingredients:\n"
                "- 400g pasta\n"
                "- 2 cans crushed tomatoes\n"
                "- 3 cloves garlic, minced\n"
                "- Fresh basil leaves\n"
                "- 3 tbsp olive oil\n"
                "- Salt and pepper to taste\n\n"
                "### Instructions:\n"
                "1. Cook pasta according to package directions until al dente\n"
                "2. Meanwhile, heat olive oil in a large pan over medium heat\n"
                "3. Sauté garlic until fragrant (about 1 minute)\n"
                "4. Add crushed tomatoes and simmer for 10-15 minutes\n"
                "5. Season with salt and pepper\n"
                "6. Toss cooked pasta with sauce\n"
                "7. Garnish with fresh basil and serve immediately\n\n"
                "**Enjoy your homemade pasta!**"
            )

        elif any(word in last_message for word in ["chicken", "poultry"]):
            logger.info("Matched chicken keywords")
            return (
                "Chicken is so versatile! Here's a quick and delicious recipe:\n\n"
                "## Herb-Roasted Chicken\n\n"
                "### Ingredients:\n"
                "- 4 chicken breasts (boneless, skinless)\n"
                "- 2 tbsp olive oil\n"
                "- 1 tsp dried thyme\n"
                "- 1 tsp dried rosemary\n"
                "- 1 tsp garlic powder\n"
                "- Salt and pepper to taste\n\n"
                "### Instructions:\n"
                "1. Preheat oven to 375°F (190°C)\n"
                "2. Pat chicken breasts dry with paper towels\n"
                "3. Rub chicken with olive oil on both sides\n"
                "4. Mix all seasonings in a small bowl\n"
                "5. Season chicken evenly with herb mixture\n"
                "6. Place on baking sheet lined with parchment paper\n"
                "7. Bake for 25-30 minutes until internal temperature reaches 165°F\n"
                "8. Let rest for 5 minutes before slicing\n\n"
                "**Perfect with roasted vegetables or a fresh salad!**"
            )

        elif any(
            word in last_message for word in ["dessert", "sweet", "cake", "cookie"]
        ):
            logger.info("Matched dessert keywords")
            return (
                "Let's make something sweet! Here's an easy and delicious dessert:\n\n"
                "## Classic Chocolate Chip Cookies\n\n"
                "### Ingredients:\n"
                "- 2¼ cups all-purpose flour\n"
                "- 1 cup butter, softened\n"
                "- ¾ cup granulated white sugar\n"
                "- ¾ cup packed brown sugar\n"
                "- 2 large eggs\n"
                "- 2 tsp vanilla extract\n"
                "- 1 tsp baking soda\n"
                "- 1 tsp salt\n"
                "- 2 cups chocolate chips\n\n"
                "### Instructions:\n"
                "1. Preheat oven to 375°F (190°C)\n"
                "2. In a large bowl, cream together butter and both sugars\n"
                "3. Beat in eggs one at a time, then add vanilla\n"
                "4. In separate bowl, whisk together flour, baking soda, and salt\n"
                "5. Gradually mix dry ingredients into wet ingredients\n"
                "6. Stir in chocolate chips\n"
                "7. Drop rounded tablespoons of dough onto ungreased baking sheets\n"
                "8. Bake for 9-11 minutes until golden brown\n"
                "9. Cool on baking sheet for 2 minutes, then transfer to wire rack\n\n"
                "**Enjoy them warm with a glass of milk!**"
            )

        else:
            logger.info("No keywords matched, returning generic response")
            return (
                "I'm here to help you create amazing recipes! Tell me what "
                "ingredients you have or what type of dish you're craving, and "
                "I'll suggest something delicious. I can help with everything from "
                "quick weeknight dinners to special occasion treats!"
            )


# Global LLM service instance
llm_service = LLMService()
