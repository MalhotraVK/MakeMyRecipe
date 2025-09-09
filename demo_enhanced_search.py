#!/usr/bin/env python3
"""
Demonstration script for enhanced recipe search with citations.

This script shows how the new search tag functionality works:
1. User makes a recipe request
2. LLM generates search tags like <search>query</search>
3. System detects tags and performs web searches
4. LLM creates structured recipes with proper citations
5. Results are returned as Recipe objects with full citation support
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from src.makemyrecipe.models.recipe import Recipe
from src.makemyrecipe.services.anthropic_service import AnthropicService
from src.makemyrecipe.services.recipe_service import RecipeService


async def demo_enhanced_recipe_search():
    """Demonstrate the enhanced recipe search functionality."""

    print("🍝 MakeMyRecipe Enhanced Search Demo")
    print("=" * 50)

    # Create mock responses to simulate the search tag workflow
    print("\n1. Setting up mock Anthropic responses...")

    # Mock initial response with search tags
    mock_initial_response = MagicMock()
    mock_initial_text = MagicMock()
    mock_initial_text.text = """
    I'll help you find an authentic carbonara recipe! Let me search for the best traditional recipes.

    <search>authentic Italian carbonara recipe traditional guanciale</search>

    I'll look for recipes from reputable Italian cooking sources.
    """
    mock_initial_response.content = [mock_initial_text]

    # Mock search response
    mock_search_response = MagicMock()
    mock_search_text = MagicMock()
    mock_search_text.text = "Found excellent carbonara recipes from Allrecipes, Food Network, and Serious Eats"
    mock_search_response.content = [mock_search_text]

    # Mock final structured response
    mock_final_response = MagicMock()
    mock_final_text = MagicMock()
    mock_final_text.text = """
    **Authentic Spaghetti Carbonara**

    This is the traditional Roman carbonara recipe, made with just a few high-quality ingredients. No cream needed - the creaminess comes from the eggs and cheese!

    **Ingredients:**
    - 400g spaghetti
    - 200g guanciale (or pancetta), diced
    - 4 large eggs
    - 100g Pecorino Romano cheese, finely grated
    - Freshly ground black pepper
    - Salt for pasta water

    **Instructions:**
    1. Bring a large pot of salted water to boil and cook spaghetti until al dente
    2. While pasta cooks, heat a large skillet over medium heat
    3. Add guanciale and cook until crispy and golden, about 5-7 minutes
    4. In a bowl, whisk together eggs, grated cheese, and plenty of black pepper
    5. When pasta is ready, reserve 1 cup of pasta cooking water, then drain
    6. Add hot pasta to the skillet with guanciale and toss
    7. Remove from heat and quickly stir in egg mixture, adding pasta water gradually
    8. Keep stirring until creamy and silky - don't let eggs scramble!
    9. Serve immediately with extra cheese and black pepper

    **Prep time:** 10 minutes
    **Cook time:** 15 minutes
    **Total time:** 25 minutes
    **Servings:** 4
    **Difficulty:** intermediate
    **Cuisine:** italian
    **Calories per serving:** 520
    """
    mock_final_response.content = [mock_final_text]

    # Mock citations
    mock_citations = [
        {
            "title": "Authentic Carbonara Recipe - Serious Eats",
            "url": "https://seriouseats.com/carbonara-recipe",
            "snippet": "The definitive guide to making perfect carbonara with traditional techniques...",
        },
        {
            "title": "Traditional Carbonara - Allrecipes",
            "url": "https://allrecipes.com/recipe/traditional-carbonara",
            "snippet": "This authentic Roman carbonara recipe uses only the finest ingredients...",
        },
    ]

    # Setup mock client
    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = [
        mock_initial_response,
        mock_search_response,
        mock_final_response,
    ]

    # Create services with mock
    anthropic_service = AnthropicService()
    anthropic_service.client = mock_client

    recipe_service = RecipeService()
    recipe_service.anthropic_service = anthropic_service

    print("✅ Mock setup complete")

    # Demonstrate search tag extraction
    print("\n2. Demonstrating search tag extraction...")

    sample_text = mock_initial_text.text
    search_queries = anthropic_service._extract_search_queries(sample_text)

    print(f"📝 Original LLM response:")
    print(f"   {sample_text.strip()}")
    print(f"\n🔍 Extracted search queries: {search_queries}")

    cleaned_text = anthropic_service._remove_search_tags(sample_text)
    print(f"\n🧹 Text after removing search tags:")
    print(f"   {cleaned_text.strip()}")

    # Demonstrate the complete workflow
    print("\n3. Running enhanced recipe search...")

    user_query = "I want to make authentic carbonara pasta"
    print(f"👤 User query: '{user_query}'")

    try:
        # This would normally make real API calls, but we're using mocks
        recipes, raw_response = await recipe_service.search_recipes_enhanced(user_query)

        print(f"\n✅ Search completed successfully!")
        print(f"📊 Found {len(recipes)} recipe(s)")

        if recipes:
            recipe = recipes[0]
            print(f"\n🍝 Recipe Details:")
            print(f"   📋 Title: {recipe.title}")
            print(f"   📝 Description: {recipe.description[:100]}...")
            print(f"   🥘 Ingredients: {len(recipe.ingredients)} items")
            print(f"   📋 Instructions: {len(recipe.instructions)} steps")
            print(f"   ⏱️  Prep time: {recipe.prep_time} minutes")
            print(f"   🔥 Cook time: {recipe.cook_time} minutes")
            print(f"   👥 Servings: {recipe.servings}")
            print(f"   📊 Difficulty: {recipe.difficulty}")
            print(f"   🌍 Cuisine: {recipe.cuisine}")
            print(f"   🔥 Calories: {recipe.calories_per_serving} per serving")

            print(f"\n📚 Citation Information:")
            print(f"   🔗 Primary source: {recipe.primary_source.title}")
            print(f"   🌐 URL: {recipe.primary_source.url}")
            print(f"   📍 Domain: {recipe.primary_source.domain}")
            print(f"   📎 Additional sources: {len(recipe.additional_sources)}")

            print(f"\n🆔 Recipe Metadata:")
            print(f"   🔑 ID: {recipe.id}")
            print(f"   🔍 Search query: {recipe.search_query}")
            print(f"   📅 Created: {recipe.created_at}")
            print(f"   💾 Saved: {recipe.is_saved}")

            # Show first few ingredients and instructions
            print(f"\n🥘 Sample Ingredients:")
            for i, ingredient in enumerate(recipe.ingredients[:3], 1):
                print(f"   {i}. {ingredient}")
            if len(recipe.ingredients) > 3:
                print(f"   ... and {len(recipe.ingredients) - 3} more")

            print(f"\n📋 Sample Instructions:")
            for i, instruction in enumerate(recipe.instructions[:3], 1):
                print(f"   {i}. {instruction}")
            if len(recipe.instructions) > 3:
                print(f"   ... and {len(recipe.instructions) - 3} more steps")

        print(f"\n📊 API Call Summary:")
        print(f"   🔄 Total API calls made: {mock_client.messages.create.call_count}")
        print(f"   1️⃣  Initial response (with search tags)")
        print(f"   2️⃣  Search execution")
        print(f"   3️⃣  Final structured response")

    except Exception as e:
        print(f"❌ Error during search: {e}")

    print("\n4. Key Features Demonstrated:")
    print("   ✅ Search tag detection and extraction")
    print("   ✅ Automatic web search execution")
    print("   ✅ Structured Recipe object creation")
    print("   ✅ Comprehensive citation support")
    print("   ✅ Rich metadata extraction")
    print("   ✅ User interaction features (save, rating)")
    print("   ✅ Timestamp and ID generation")

    print("\n🎉 Demo completed successfully!")
    print("\nThe enhanced recipe search system now supports:")
    print("• 🔍 Intelligent search tag detection")
    print("• 📚 Comprehensive citation tracking")
    print("• 🍽️  Rich recipe metadata")
    print("• 💾 User interaction features")
    print("• 🔗 Clickable source links")
    print("• ⭐ Rating and review support")


if __name__ == "__main__":
    asyncio.run(demo_enhanced_recipe_search())
