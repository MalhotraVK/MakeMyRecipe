"""LLM service for generating chat responses."""

from typing import TYPE_CHECKING, Any, List, Optional, cast

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
        if litellm_module is None:
            logger.warning("LiteLLM not available, returning mock response")
            return self._get_mock_response(messages)

        return await self._generate_with_litellm(messages, system_prompt)

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

            content = cast(Optional[str], response.choices[0].message.content)
            return content if content is not None else self._get_mock_response(messages)

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

        # Simple keyword-based responses
        if any(word in last_message for word in ["pasta", "spaghetti", "noodles"]):
            return (
                "I'd love to help you make pasta! Here's a simple and delicious "
                "recipe:\n\n**Classic Tomato Pasta**\n\nIngredients:\n- 400g pasta\n"
                "- 2 cans crushed tomatoes\n- 3 cloves garlic\n- Fresh basil\n"
                "- Olive oil\n- Salt and pepper\n\nCook pasta according to package "
                "directions. Meanwhile, sauté garlic in olive oil, add tomatoes and "
                "simmer. Toss with pasta and fresh basil. Enjoy!"
            )

        elif any(word in last_message for word in ["chicken", "poultry"]):
            return (
                "Chicken is so versatile! Here's a quick recipe:\n\n"
                "**Herb-Roasted Chicken**\n\nIngredients:\n- 4 chicken breasts\n"
                "- 2 tbsp olive oil\n- 1 tsp each: thyme, rosemary, garlic powder\n"
                "- Salt and pepper\n\nRub chicken with oil and seasonings. "
                "Bake at 375°F for 25-30 minutes until cooked through. "
                "Perfect with roasted vegetables!"
            )

        elif any(
            word in last_message for word in ["dessert", "sweet", "cake", "cookie"]
        ):
            return (
                "Let's make something sweet! Here's an easy dessert:\n\n"
                "**Chocolate Chip Cookies**\n\nIngredients:\n- 2¼ cups flour\n"
                "- 1 cup butter, softened\n- ¾ cup each: white and brown sugar\n"
                "- 2 eggs\n- 2 tsp vanilla\n- 1 tsp baking soda\n- 1 tsp salt\n"
                "- 2 cups chocolate chips\n\nMix ingredients, drop on baking sheet, "
                "bake at 375°F for 9-11 minutes. Enjoy warm!"
            )

        else:
            return (
                "I'm here to help you create amazing recipes! Tell me what "
                "ingredients you have or what type of dish you're craving, and "
                "I'll suggest something delicious. I can help with everything from "
                "quick weeknight dinners to special occasion treats!"
            )


# Global LLM service instance
llm_service = LLMService()
