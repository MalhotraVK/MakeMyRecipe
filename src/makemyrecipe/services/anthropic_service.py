"""Anthropic Claude API service with web search integration."""

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import Message, MessageParam, ToolParam, ToolUseBlock

from ..core.config import settings
from ..core.logging import get_logger
from ..models.chat import ChatMessage

logger = get_logger(__name__)


class AnthropicService:
    """Service for interacting with Anthropic Claude API with web search."""

    def __init__(self) -> None:
        """Initialize the Anthropic service."""
        self.client: Optional[AsyncAnthropic] = None
        self.sync_client: Optional[Anthropic] = None
        self._rate_limiter = RateLimiter(
            max_requests_per_minute=settings.anthropic_rate_limit_rpm
        )
        self._setup_client()

    def _setup_client(self) -> None:
        """Set up the Anthropic client."""
        if not settings.anthropic_api_key:
            logger.warning("Anthropic API key not provided")
            return

        try:
            self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            self.sync_client = Anthropic(api_key=settings.anthropic_api_key)
            logger.info("Anthropic client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")

    def _get_web_search_tool(self) -> ToolParam:
        """Get the web search tool configuration."""
        return {
            "type": "web_search_20250305",
            "name": "web_search",
        }

    def _create_recipe_system_prompt(self) -> str:
        """Create a system prompt optimized for recipe queries with search tags."""
        return (
            "You are MakeMyRecipe, an expert culinary AI assistant "
            "specializing in recipe recommendations and cooking guidance.\n\n"
            "Your capabilities include:\n"
            "- Searching the web for authentic recipes from trusted cooking websites\n"
            "- Providing detailed cooking instructions with precise measurements\n"
            "- Suggesting ingredient substitutions and dietary modifications\n"
            "- Offering cooking tips and techniques\n"
            "- Finding recipes based on available ingredients\n"
            "- Recommending recipes from specific cuisines or dietary preferences\n\n"
            "IMPORTANT FORMATTING INSTRUCTIONS:\n"
            "Always format your recipe responses using proper markdown:\n"
            "- Use ## for recipe titles (e.g., ## Classic Spaghetti Carbonara)\n"
            "- Use ### for section headers (e.g., ### Ingredients:, "
            "### Instructions:)\n"
            "- Use - for ingredient lists (e.g., - 400g spaghetti)\n"
            "- Use numbered lists for instructions (e.g., 1. Boil water)\n"
            "- Use **bold** for emphasis and important notes\n"
            "- Include proper URLs when referencing sources\n\n"
            "IMPORTANT SEARCH INSTRUCTIONS:\n"
            "When you need to search for recipes or cooking information, "
            "you must use search tags.\n"
            "Format your search queries using: "
            "<search>your search query here</search>\n\n"
            "Examples of when to use search tags:\n"
            "- User asks for a specific recipe: "
            "<search>authentic Italian carbonara recipe</search>\n"
            "- User wants recipes with ingredients: "
            "<search>chicken breast recipes with garlic and herbs</search>\n"
            "- User asks about cooking techniques: "
            "<search>how to properly sear steak cooking technique</search>\n"
            "- User wants cuisine-specific recipes: "
            "<search>traditional Thai pad thai recipe</search>\n\n"
            "Search query guidelines:\n"
            "- Include specific ingredients, cuisine types, or cooking methods\n"
            "- Add terms like 'recipe', 'cooking', 'technique' for better results\n"
            "- Focus on reputable cooking sites "
            "(allrecipes, food network, serious eats, etc.)\n"
            "- Be specific about dietary restrictions or preferences\n\n"
            "After searching, always:\n"
            "1. Provide complete ingredient lists with precise measurements\n"
            "2. Include detailed step-by-step cooking instructions\n"
            "3. Mention prep time, cook time, and serving size\n"
            "4. Include source citations with clickable links\n"
            "5. Suggest variations or substitutions when relevant\n"
            "6. Provide cooking tips and techniques for best results\n\n"
            "Focus on providing practical, actionable cooking advice with "
            "verified information from reliable sources."
        )

    def _extract_search_queries(self, text: str) -> List[str]:
        """Extract search queries from <search></search> tags."""
        pattern = r"<search>(.*?)</search>"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        return [match.strip() for match in matches if match.strip()]

    def _remove_search_tags(self, text: str) -> str:
        """Remove search tags from text."""
        pattern = r"<search>.*?</search>"
        return re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE).strip()

    async def _perform_search(self, query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Perform a web search using Anthropic's search API."""
        if not self.client:
            logger.warning("Anthropic client not available for search")
            return "", []

        try:
            # Create a search-focused message
            search_message = ChatMessage(role="user", content=f"Search for: {query}")

            # Use the web search tool
            claude_messages = self._convert_messages([search_message])

            response = await self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                temperature=0.1,  # Lower temperature for search
                system=(
                    "You are a web search assistant. Search for the requested "
                    "information and provide relevant results."
                ),
                messages=claude_messages,
                tools=[self._get_web_search_tool()],
            )

            # Extract search results
            content, citations = self._extract_response_content(response)
            return content, citations

        except Exception as e:
            logger.error(f"Error performing search: {e}")
            return f"Search error: {str(e)}", []

    async def generate_recipe_response(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
        use_web_search: bool = True,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generate a recipe response using Claude with search tag detection.

        Returns:
            Tuple of (response_content, citations)
        """
        if not self.client:
            logger.warning("Anthropic client not available")
            return self._get_fallback_response(messages), []

        try:
            # Apply rate limiting
            await self._rate_limiter.wait_if_needed()

            # Prepare messages
            claude_messages = self._convert_messages(messages)

            # Use recipe-optimized system prompt if none provided
            if not system_prompt:
                system_prompt = self._create_recipe_system_prompt()

            # First, generate initial response without web search to detect search tags
            initial_response = await self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                temperature=settings.anthropic_temperature,
                system=system_prompt,
                messages=claude_messages,
            )

            # Extract initial content
            initial_content, _ = self._extract_response_content(initial_response)

            # Check for search tags
            search_queries = self._extract_search_queries(initial_content)
            all_citations = []
            search_results_content = ""

            if search_queries and use_web_search:
                logger.info(
                    f"Found {len(search_queries)} search queries: {search_queries}"
                )

                # Perform searches for each query
                for query in search_queries:
                    search_content, search_citations = await self._perform_search(query)
                    search_results_content += (
                        f"\n\nSearch results for '{query}':\n{search_content}"
                    )
                    all_citations.extend(search_citations)

                # Remove search tags from initial content
                cleaned_content = self._remove_search_tags(initial_content)

                # Generate final response with search results
                final_messages = claude_messages + [
                    {"role": "assistant", "content": cleaned_content},
                    {
                        "role": "user",
                        "content": (
                            f"Here are the search results for your queries:"
                            f"{search_results_content}\n\n"
                            "Please provide a comprehensive recipe response based on "
                            "this information, including proper citations."
                        ),
                    },
                ]

                final_response = await self.client.messages.create(
                    model=settings.anthropic_model,
                    max_tokens=settings.anthropic_max_tokens,
                    temperature=settings.anthropic_temperature,
                    system=system_prompt,
                    messages=final_messages,
                )

                final_content, final_citations = self._extract_response_content(
                    final_response
                )
                all_citations.extend(final_citations)

                # Update rate limiter for multiple calls
                self._rate_limiter.update_usage()
                self._rate_limiter.update_usage()

                return final_content, all_citations
            else:
                # No search tags found, return initial response
                # Update rate limiter
                self._rate_limiter.update_usage()
                return initial_content, []

        except Exception as e:
            logger.error(f"Error generating Anthropic response: {e}")
            return self._get_fallback_response(messages), []

    def _convert_messages(self, messages: List[ChatMessage]) -> List[MessageParam]:
        """Convert ChatMessage objects to Anthropic message format."""
        claude_messages: List[MessageParam] = []

        for msg in messages:
            if msg.role in ["user", "assistant"]:
                claude_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        return claude_messages

    def _extract_response_content(
        self, response: Message
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Extract content and citations from Claude response."""
        content_parts = []
        citations = []

        for block in response.content:
            if hasattr(block, "text"):
                content_parts.append(block.text)
            elif isinstance(block, ToolUseBlock):
                # Handle tool use results (web search results)
                if hasattr(block, "input") and isinstance(block.input, dict):
                    search_results = block.input.get("results", [])
                    for result in search_results:
                        if isinstance(result, dict):
                            citations.append(
                                {
                                    "title": result.get("title", ""),
                                    "url": result.get("url", ""),
                                    "snippet": result.get("snippet", ""),
                                }
                            )

        content = "\n".join(content_parts) if content_parts else ""

        # If we have citations, append them to the content
        if citations:
            content += "\n\n**Sources:**\n"
            for i, citation in enumerate(citations, 1):
                content += f"{i}. [{citation['title']}]({citation['url']})\n"

        return content, citations

    def _get_fallback_response(self, messages: List[ChatMessage]) -> str:
        """Generate a fallback response when Anthropic API is not available."""
        if not messages:
            return (
                "Hello! I'm MakeMyRecipe, your AI cooking assistant. "
                "I can help you find recipes, cooking tips, and ingredient "
                "suggestions. What would you like to cook today?"
            )

        last_message = messages[-1].content.lower()

        # Enhanced keyword-based responses for recipe queries
        if any(word in last_message for word in ["recipe", "cook", "make", "how to"]):
            return (
                "I'd love to help you with that recipe! While I'm currently "
                "unable to search for the latest recipes online, I can suggest "
                "some classic approaches. Could you tell me more about what "
                "ingredients you have available or what type of cuisine you're "
                "interested in?"
            )

        return (
            "I'm here to help you with cooking and recipes! Please let me know what "
            "you'd like to make, and I'll do my best to assist you with ingredients, "
            "cooking techniques, and step-by-step instructions."
        )


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, max_requests_per_minute: int = 50) -> None:
        """Initialize rate limiter."""
        self.max_requests_per_minute = max_requests_per_minute
        self.requests: List[float] = []
        self.lock = asyncio.Lock()

    async def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        async with self.lock:
            now = time.time()

            # Remove requests older than 1 minute
            self.requests = [
                req_time for req_time in self.requests if now - req_time < 60
            ]

            # Check if we need to wait
            if len(self.requests) >= self.max_requests_per_minute:
                if self.requests:  # Only proceed if we have requests
                    oldest_request = min(self.requests)
                    wait_time = 60 - (now - oldest_request)
                    if wait_time > 0:
                        logger.info(
                            f"Rate limit reached, waiting {wait_time:.2f} seconds"
                        )
                        await asyncio.sleep(wait_time)

    def update_usage(self) -> None:
        """Update usage tracking."""
        self.requests.append(time.time())


# Global Anthropic service instance
anthropic_service = AnthropicService()
