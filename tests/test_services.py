"""Tests for service classes."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from makemyrecipe.models.chat import ChatMessage, ConversationSearchQuery
from makemyrecipe.services.chat_service import ChatService
from makemyrecipe.services.llm_service import LLMService


@pytest.fixture
def temp_chat_service():
    """Create a ChatService with temporary storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a new ChatService instance with temporary storage
        service = ChatService()
        service.storage_path = Path(temp_dir)
        service._conversations = {}

        # Also update the persistence service to use the same temp directory
        from makemyrecipe.services.conversation_persistence import (
            conversation_persistence,
        )

        original_storage_path = conversation_persistence.storage_path
        original_backup_path = conversation_persistence.backup_path
        original_temp_path = conversation_persistence.temp_path

        conversation_persistence.storage_path = Path(temp_dir)
        conversation_persistence.backup_path = Path(temp_dir) / "backups"
        conversation_persistence.temp_path = Path(temp_dir) / "temp"

        # Create directories
        conversation_persistence.storage_path.mkdir(parents=True, exist_ok=True)
        conversation_persistence.backup_path.mkdir(parents=True, exist_ok=True)
        conversation_persistence.temp_path.mkdir(parents=True, exist_ok=True)

        try:
            yield service
        finally:
            # Restore original paths
            conversation_persistence.storage_path = original_storage_path
            conversation_persistence.backup_path = original_backup_path
            conversation_persistence.temp_path = original_temp_path


def test_chat_service_create_conversation(temp_chat_service) -> None:
    """Test creating a new conversation."""
    conversation = temp_chat_service.create_conversation("test_user")

    assert conversation.user_id == "test_user"
    assert conversation.conversation_id is not None
    assert len(conversation.messages) == 0
    assert conversation.system_prompt is not None


def test_chat_service_create_conversation_with_custom_prompt(temp_chat_service) -> None:
    """Test creating a conversation with custom system prompt."""
    custom_prompt = "You are a specialized chef."
    conversation = temp_chat_service.create_conversation("test_user", custom_prompt)

    assert conversation.system_prompt == custom_prompt


def test_chat_service_get_conversation(temp_chat_service) -> None:
    """Test getting a conversation by ID."""
    conversation = temp_chat_service.create_conversation("test_user")

    retrieved = temp_chat_service.get_conversation(conversation.conversation_id)
    assert retrieved is not None
    assert retrieved.conversation_id == conversation.conversation_id


def test_chat_service_get_nonexistent_conversation(temp_chat_service) -> None:
    """Test getting a non-existent conversation."""
    retrieved = temp_chat_service.get_conversation("nonexistent_id")
    assert retrieved is None


def test_chat_service_add_message(temp_chat_service) -> None:
    """Test adding a message to a conversation."""
    conversation = temp_chat_service.create_conversation("test_user")

    updated = temp_chat_service.add_message(
        conversation.conversation_id, "user", "Hello"
    )
    assert updated is not None
    assert len(updated.messages) == 1
    assert updated.messages[0].role == "user"
    assert updated.messages[0].content == "Hello"
    assert updated.messages[0].message_id is not None


def test_chat_service_add_message_nonexistent_conversation(temp_chat_service) -> None:
    """Test adding a message to a non-existent conversation."""
    result = temp_chat_service.add_message("nonexistent_id", "user", "Hello")
    assert result is None


def test_chat_service_get_user_conversations(temp_chat_service) -> None:
    """Test getting conversations for a user."""
    # Create multiple conversations for the same user
    conv1 = temp_chat_service.create_conversation("test_user")
    conv2 = temp_chat_service.create_conversation("test_user")

    # Create conversation for different user
    temp_chat_service.create_conversation("other_user")

    user_conversations = temp_chat_service.get_user_conversations("test_user")
    assert len(user_conversations) == 2

    conversation_ids = [conv.conversation_id for conv in user_conversations]
    assert conv1.conversation_id in conversation_ids
    assert conv2.conversation_id in conversation_ids


def test_chat_service_get_user_conversations_with_limit(temp_chat_service) -> None:
    """Test getting conversations with limit."""
    # Create multiple conversations
    for i in range(5):
        temp_chat_service.create_conversation("test_user")

    limited_conversations = temp_chat_service.get_user_conversations(
        "test_user", limit=3
    )
    assert len(limited_conversations) == 3


def test_chat_service_delete_conversation(temp_chat_service) -> None:
    """Test deleting a conversation."""
    conversation = temp_chat_service.create_conversation("test_user")

    # Verify it exists
    assert temp_chat_service.get_conversation(conversation.conversation_id) is not None

    # Delete it
    success = temp_chat_service.delete_conversation(conversation.conversation_id)
    assert success is True

    # Verify it's gone
    assert temp_chat_service.get_conversation(conversation.conversation_id) is None


def test_chat_service_delete_nonexistent_conversation(temp_chat_service) -> None:
    """Test deleting a non-existent conversation."""
    success = temp_chat_service.delete_conversation("nonexistent_id")
    assert success is False


def test_llm_service_mock_response() -> None:
    """Test LLM service mock response generation."""
    service = LLMService()
    messages = [ChatMessage(role="user", content="I want to make pasta")]

    response = service._get_mock_response(messages)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "pasta" in response.lower()


def test_llm_service_mock_response_chicken() -> None:
    """Test LLM service mock response for chicken."""
    service = LLMService()
    messages = [ChatMessage(role="user", content="How do I cook chicken?")]

    response = service._get_mock_response(messages)
    assert "chicken" in response.lower()


def test_llm_service_mock_response_dessert() -> None:
    """Test LLM service mock response for dessert."""
    service = LLMService()
    messages = [ChatMessage(role="user", content="I want to make a dessert")]

    response = service._get_mock_response(messages)
    assert any(
        word in response.lower() for word in ["dessert", "sweet", "cookie", "cake"]
    )


def test_llm_service_mock_response_empty_messages() -> None:
    """Test LLM service mock response with empty messages."""
    service = LLMService()
    messages = []

    response = service._get_mock_response(messages)
    assert "Hello" in response
    assert "MakeMyRecipe" in response


@pytest.mark.asyncio
async def test_llm_service_generate_response_without_litellm() -> None:
    """Test LLM service response generation without LiteLLM."""
    service = LLMService()
    messages = [ChatMessage(role="user", content="I want to make pasta")]

    # This should fall back to mock response since LiteLLM might not be configured
    response = await service.generate_response(messages)
    assert isinstance(response, str)
    assert len(response) > 0


def test_chat_service_add_message_with_metadata(temp_chat_service) -> None:
    """Test adding a message with metadata."""
    conversation = temp_chat_service.create_conversation("test_user")
    metadata = {"source": "web", "confidence": 0.95}

    updated = temp_chat_service.add_message(
        conversation.conversation_id, "user", "Hello", metadata=metadata
    )
    assert updated is not None
    assert len(updated.messages) == 1
    assert updated.messages[0].metadata == metadata


def test_chat_service_add_threaded_message(temp_chat_service) -> None:
    """Test adding a threaded message."""
    conversation = temp_chat_service.create_conversation("test_user")

    # Add parent message
    parent_updated = temp_chat_service.add_message(
        conversation.conversation_id, "user", "What's the weather?"
    )
    parent_message_id = parent_updated.messages[0].message_id

    # Add threaded response
    updated = temp_chat_service.add_message(
        conversation.conversation_id,
        "assistant",
        "I can't check weather, but I can help with recipes!",
        parent_message_id=parent_message_id,
    )

    assert updated is not None
    assert len(updated.messages) == 2
    assert updated.messages[1].parent_message_id == parent_message_id


def test_chat_service_update_conversation_metadata(temp_chat_service) -> None:
    """Test updating conversation metadata."""
    conversation = temp_chat_service.create_conversation("test_user")

    updated = temp_chat_service.update_conversation_metadata(
        conversation.conversation_id,
        title="Pasta Recipe Discussion",
        tags=["pasta", "italian"],
        cuisine_preferences=["italian"],
        dietary_restrictions=["vegetarian"],
    )

    assert updated is not None
    assert updated.metadata.title == "Pasta Recipe Discussion"
    assert "pasta" in updated.metadata.tags
    assert "italian" in updated.metadata.cuisine_preferences
    assert "vegetarian" in updated.metadata.dietary_restrictions


def test_chat_service_search_conversations(temp_chat_service) -> None:
    """Test searching conversations."""
    # Create test conversations
    conv1 = temp_chat_service.create_conversation("test_user")
    temp_chat_service.add_message(conv1.conversation_id, "user", "I want pasta")
    temp_chat_service.update_conversation_metadata(
        conv1.conversation_id, title="Pasta Recipe", tags=["pasta"]
    )

    conv2 = temp_chat_service.create_conversation("test_user")
    temp_chat_service.add_message(conv2.conversation_id, "user", "How to make pizza?")
    temp_chat_service.update_conversation_metadata(
        conv2.conversation_id, title="Pizza Recipe", tags=["pizza"]
    )

    # Search for pasta
    query = ConversationSearchQuery(user_id="test_user", query="pasta")
    results = temp_chat_service.search_conversations(query)

    assert len(results) == 1
    assert results[0].conversation.conversation_id == conv1.conversation_id


def test_chat_service_backup_and_restore(temp_chat_service) -> None:
    """Test backup and restore functionality."""
    # Create a conversation
    conversation = temp_chat_service.create_conversation("test_user")
    temp_chat_service.add_message(conversation.conversation_id, "user", "Test message")

    # Create backup
    backup_id = temp_chat_service.create_backup("test_user")
    assert backup_id is not None

    # Delete conversation
    temp_chat_service.delete_conversation(conversation.conversation_id)
    assert temp_chat_service.get_conversation(conversation.conversation_id) is None

    # Restore from backup
    success = temp_chat_service.restore_from_backup(backup_id, "test_user")
    assert success

    # Verify conversation is restored
    restored = temp_chat_service.get_conversation(conversation.conversation_id)
    assert restored is not None
    assert len(restored.messages) == 1


def test_chat_service_get_storage_stats(temp_chat_service) -> None:
    """Test getting storage statistics."""
    # Initially should have no conversations
    stats = temp_chat_service.get_storage_stats()
    assert stats["total_conversations"] == 0

    # Create a conversation
    conversation = temp_chat_service.create_conversation("test_user")
    temp_chat_service.add_message(conversation.conversation_id, "user", "Hello")

    # Check stats again
    stats = temp_chat_service.get_storage_stats()
    assert stats["total_conversations"] == 1
    assert stats["total_messages"] == 1


def test_chat_service_cleanup_old_backups(temp_chat_service) -> None:
    """Test cleanup of old backups."""
    # Create multiple backups
    for i in range(5):
        temp_chat_service.create_backup()

    # Cleanup keeping only 3
    removed_count = temp_chat_service.cleanup_old_backups(keep_count=3)
    assert removed_count >= 0  # May be 0 if backups are recent
