"""Tests for conversation persistence service."""

import gzip
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from makemyrecipe.models.chat import (
    ChatMessage,
    Conversation,
    ConversationMetadata,
    ConversationSearchQuery,
)
from makemyrecipe.services.conversation_persistence import (
    ConversationPersistenceService,
)


@pytest.fixture
def temp_persistence_service():
    """Create a ConversationPersistenceService with temporary storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        service = ConversationPersistenceService()
        service.storage_path = Path(temp_dir) / "conversations"
        service.backup_path = Path(temp_dir) / "backups"
        service.temp_path = Path(temp_dir) / "temp"

        # Create directories
        service.storage_path.mkdir(parents=True, exist_ok=True)
        service.backup_path.mkdir(parents=True, exist_ok=True)
        service.temp_path.mkdir(parents=True, exist_ok=True)

        yield service


@pytest.fixture
def sample_conversation():
    """Create a sample conversation for testing."""
    conversation = Conversation(user_id="test_user")
    conversation.add_message("user", "Hello, I want to make pasta")
    conversation.add_message("assistant", "I'd be happy to help you make pasta!")
    conversation.metadata.title = "Pasta Recipe Discussion"
    conversation.metadata.tags = ["pasta", "italian", "cooking"]
    conversation.metadata.cuisine_preferences = ["italian"]
    return conversation


def test_calculate_checksum(temp_persistence_service):
    """Test checksum calculation."""
    data = "test data"
    checksum1 = temp_persistence_service.calculate_checksum(data)
    checksum2 = temp_persistence_service.calculate_checksum(data)

    assert checksum1 == checksum2
    assert len(checksum1) == 64  # SHA-256 hex length

    # Different data should produce different checksums
    different_checksum = temp_persistence_service.calculate_checksum("different data")
    assert checksum1 != different_checksum


def test_validate_conversation_data(temp_persistence_service):
    """Test conversation data validation."""
    # Valid data
    valid_data = {
        "conversation_id": "test_id",
        "user_id": "test_user",
        "messages": [
            {"role": "user", "content": "Hello", "timestamp": "2023-01-01T00:00:00Z"}
        ],
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
    }

    is_valid, errors = temp_persistence_service.validate_conversation_data(valid_data)
    assert is_valid
    assert len(errors) == 0

    # Invalid data - missing required field
    invalid_data = valid_data.copy()
    del invalid_data["user_id"]

    is_valid, errors = temp_persistence_service.validate_conversation_data(invalid_data)
    assert not is_valid
    assert "Missing required field: user_id" in errors

    # Invalid message role
    invalid_role_data = valid_data.copy()
    invalid_role_data["messages"] = [
        {
            "role": "invalid_role",
            "content": "Hello",
            "timestamp": "2023-01-01T00:00:00Z",
        }
    ]

    is_valid, errors = temp_persistence_service.validate_conversation_data(
        invalid_role_data
    )
    assert not is_valid
    assert any("invalid role" in error.lower() for error in errors)


def test_save_and_load_conversation(temp_persistence_service, sample_conversation):
    """Test saving and loading conversations with validation."""
    # Save conversation
    success = temp_persistence_service.save_conversation_with_validation(
        sample_conversation
    )
    assert success

    # Verify file exists
    file_path = (
        temp_persistence_service.storage_path
        / f"{sample_conversation.conversation_id}.json"
    )
    assert file_path.exists()

    # Load conversation
    loaded_conversation = temp_persistence_service.load_conversation_with_validation(
        sample_conversation.conversation_id
    )
    assert loaded_conversation is not None
    assert loaded_conversation.conversation_id == sample_conversation.conversation_id
    assert loaded_conversation.user_id == sample_conversation.user_id
    assert len(loaded_conversation.messages) == len(sample_conversation.messages)
    assert loaded_conversation.metadata.title == sample_conversation.metadata.title
    assert loaded_conversation.checksum is not None


def test_load_nonexistent_conversation(temp_persistence_service):
    """Test loading a non-existent conversation."""
    result = temp_persistence_service.load_conversation_with_validation(
        "nonexistent_id"
    )
    assert result is None


def test_checksum_verification(temp_persistence_service, sample_conversation):
    """Test checksum verification during load."""
    # Save conversation
    temp_persistence_service.save_conversation_with_validation(sample_conversation)

    # Manually corrupt the file
    file_path = (
        temp_persistence_service.storage_path
        / f"{sample_conversation.conversation_id}.json"
    )
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Change content but keep checksum
    data["messages"][0]["content"] = "Corrupted content"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    # Loading should detect corruption and try to recover from backup
    # Since no backup exists, it should return None
    loaded_conversation = temp_persistence_service.load_conversation_with_validation(
        sample_conversation.conversation_id
    )
    # The conversation is loaded but checksum mismatch is detected
    # Since no backup exists, it returns None
    assert loaded_conversation is None


def test_create_backup(temp_persistence_service, sample_conversation):
    """Test creating backups."""
    # Save some conversations
    temp_persistence_service.save_conversation_with_validation(sample_conversation)

    # Create another conversation
    conversation2 = Conversation(user_id="test_user")
    conversation2.add_message("user", "How do I make pizza?")
    temp_persistence_service.save_conversation_with_validation(conversation2)

    # Create backup
    backup = temp_persistence_service.create_backup()
    assert backup is not None
    assert backup.conversation_count == 2
    assert backup.total_size > 0
    assert backup.checksum is not None

    # Verify backup file exists
    backup_file = temp_persistence_service.backup_path / f"{backup.backup_id}.json.gz"
    assert backup_file.exists()


def test_create_user_specific_backup(temp_persistence_service, sample_conversation):
    """Test creating user-specific backups."""
    # Save conversations for different users
    temp_persistence_service.save_conversation_with_validation(sample_conversation)

    other_user_conv = Conversation(user_id="other_user")
    other_user_conv.add_message("user", "Hello from other user")
    temp_persistence_service.save_conversation_with_validation(other_user_conv)

    # Create backup for specific user
    backup = temp_persistence_service.create_backup(user_id="test_user")
    assert backup is not None
    assert backup.conversation_count == 1  # Only test_user's conversation


def test_restore_from_backup(temp_persistence_service, sample_conversation):
    """Test restoring from backup."""
    # Save conversation and create backup
    temp_persistence_service.save_conversation_with_validation(sample_conversation)
    backup = temp_persistence_service.create_backup()
    assert backup is not None

    # Delete original file
    file_path = (
        temp_persistence_service.storage_path
        / f"{sample_conversation.conversation_id}.json"
    )
    file_path.unlink()

    # Restore from backup
    success = temp_persistence_service.restore_from_backup(backup.backup_id)
    assert success

    # Verify conversation is restored
    assert file_path.exists()
    loaded_conversation = temp_persistence_service.load_conversation_with_validation(
        sample_conversation.conversation_id
    )
    assert loaded_conversation is not None
    assert loaded_conversation.user_id == sample_conversation.user_id


def test_search_conversations(temp_persistence_service):
    """Test conversation search functionality."""
    # Create test conversations
    conv1 = Conversation(user_id="test_user")
    conv1.add_message("user", "I want to make pasta with tomatoes")
    conv1.metadata.title = "Pasta Recipe"
    conv1.metadata.tags = ["pasta", "italian"]
    conv1.metadata.cuisine_preferences = ["italian"]
    temp_persistence_service.save_conversation_with_validation(conv1)

    conv2 = Conversation(user_id="test_user")
    conv2.add_message("user", "How do I make pizza dough?")
    conv2.metadata.title = "Pizza Making"
    conv2.metadata.tags = ["pizza", "italian"]
    conv2.metadata.cuisine_preferences = ["italian"]
    temp_persistence_service.save_conversation_with_validation(conv2)

    conv3 = Conversation(user_id="other_user")
    conv3.add_message("user", "Sushi recipe please")
    conv3.metadata.tags = ["sushi", "japanese"]
    conv3.metadata.cuisine_preferences = ["japanese"]
    temp_persistence_service.save_conversation_with_validation(conv3)

    # Test text search
    query = ConversationSearchQuery(user_id="test_user", query="pasta")
    results = temp_persistence_service.search_conversations(query)
    assert len(results) == 1
    assert results[0].conversation.conversation_id == conv1.conversation_id
    assert results[0].relevance_score > 0

    # Test tag filter
    query = ConversationSearchQuery(user_id="test_user", tags=["italian"])
    results = temp_persistence_service.search_conversations(query)
    assert len(results) == 2

    # Test cuisine filter
    query = ConversationSearchQuery(
        user_id="test_user", cuisine_preferences=["italian"]
    )
    results = temp_persistence_service.search_conversations(query)
    assert len(results) == 2

    # Test pagination
    query = ConversationSearchQuery(user_id="test_user", limit=1)
    results = temp_persistence_service.search_conversations(query)
    assert len(results) == 1


def test_search_with_date_filter(temp_persistence_service):
    """Test search with date filtering."""
    # Create conversation with specific date
    conv = Conversation(user_id="test_user")
    conv.created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
    conv.add_message("user", "Test message")
    temp_persistence_service.save_conversation_with_validation(conv)

    # Search with date range that includes the conversation
    query = ConversationSearchQuery(
        user_id="test_user",
        date_from=datetime(2022, 12, 31, tzinfo=timezone.utc),
        date_to=datetime(2023, 1, 2, tzinfo=timezone.utc),
    )
    results = temp_persistence_service.search_conversations(query)
    assert len(results) == 1

    # Search with date range that excludes the conversation
    query = ConversationSearchQuery(
        user_id="test_user",
        date_from=datetime(2023, 1, 2, tzinfo=timezone.utc),
        date_to=datetime(2023, 1, 3, tzinfo=timezone.utc),
    )
    results = temp_persistence_service.search_conversations(query)
    assert len(results) == 0


def test_get_storage_stats(temp_persistence_service, sample_conversation):
    """Test storage statistics."""
    # Initially empty
    stats = temp_persistence_service.get_storage_stats()
    assert stats["total_conversations"] == 0
    assert stats["total_messages"] == 0

    # Save conversation
    temp_persistence_service.save_conversation_with_validation(sample_conversation)

    # Check stats
    stats = temp_persistence_service.get_storage_stats()
    assert stats["total_conversations"] == 1
    assert stats["total_messages"] == 2  # sample_conversation has 2 messages
    assert stats["total_size"] > 0


def test_cleanup_old_backups(temp_persistence_service):
    """Test cleanup of old backup files."""
    # Create multiple backup files
    for i in range(15):
        backup_file = (
            temp_persistence_service.backup_path
            / f"backup_2023010{i:02d}_120000.json.gz"
        )
        with gzip.open(backup_file, "wt", encoding="utf-8") as f:
            f.write('{"test": "data"}')

    # Cleanup, keeping only 10
    removed_count = temp_persistence_service.cleanup_old_backups(keep_count=10)
    assert removed_count == 5

    # Verify only 10 files remain
    remaining_files = list(
        temp_persistence_service.backup_path.glob("backup_*.json.gz")
    )
    assert len(remaining_files) == 10


def test_recovery_from_backup(temp_persistence_service, sample_conversation):
    """Test automatic recovery from backup when file is corrupted."""
    # Save conversation and create backup
    temp_persistence_service.save_conversation_with_validation(sample_conversation)
    backup = temp_persistence_service.create_backup()
    assert backup is not None

    # Corrupt the original file
    file_path = (
        temp_persistence_service.storage_path
        / f"{sample_conversation.conversation_id}.json"
    )
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("invalid json content")

    # Loading should recover from backup
    loaded_conversation = temp_persistence_service.load_conversation_with_validation(
        sample_conversation.conversation_id
    )
    assert loaded_conversation is not None
    assert loaded_conversation.conversation_id == sample_conversation.conversation_id


def test_conversation_threading(sample_conversation):
    """Test conversation message threading functionality."""
    # Add a threaded message
    parent_message = sample_conversation.messages[0]
    threaded_message = sample_conversation.add_message(
        "assistant",
        "This is a threaded response",
        parent_message_id=parent_message.message_id,
    )

    # Test getting thread messages
    thread_messages = sample_conversation.get_thread_messages(parent_message.message_id)
    assert len(thread_messages) == 1
    assert thread_messages[0].message_id == threaded_message.message_id

    # Test getting root messages (no parent)
    root_messages = sample_conversation.get_thread_messages(None)
    assert len(root_messages) == 2  # Original 2 messages have no parent


def test_conversation_metadata_validation():
    """Test conversation metadata validation."""
    metadata = ConversationMetadata(
        title="Test Conversation",
        tags=["test", "validation"],
        cuisine_preferences=["italian", "mexican"],
        dietary_restrictions=["vegetarian"],
    )

    conversation = Conversation(user_id="test_user", metadata=metadata)

    assert conversation.metadata.title == "Test Conversation"
    assert "test" in conversation.metadata.tags
    assert "italian" in conversation.metadata.cuisine_preferences
    assert "vegetarian" in conversation.metadata.dietary_restrictions


def test_message_validation():
    """Test message validation."""
    # Valid message
    message = ChatMessage(role="user", content="Hello")
    assert message.role == "user"
    assert message.message_id is not None

    # Invalid role should raise validation error
    with pytest.raises(ValueError, match="Role must be one of"):
        ChatMessage(role="invalid_role", content="Hello")


def test_conversation_size_estimation(sample_conversation):
    """Test conversation size estimation."""
    size = sample_conversation.get_size_estimate()
    assert size > 0
    assert isinstance(size, int)

    # Add more messages and verify size increases
    original_size = size
    sample_conversation.add_message(
        "user", "This is a longer message to increase the size"
    )
    new_size = sample_conversation.get_size_estimate()
    assert new_size > original_size


def test_atomic_file_operations(temp_persistence_service, sample_conversation):
    """Test that file operations are atomic."""

    # Mock shutil.move to fail
    def failing_move(*args, **kwargs):
        raise OSError("Simulated failure")

    # Save should fail gracefully
    with patch("shutil.move", side_effect=failing_move):
        success = temp_persistence_service.save_conversation_with_validation(
            sample_conversation
        )
        assert not success

    # Original file should not exist (atomic operation failed)
    file_path = (
        temp_persistence_service.storage_path
        / f"{sample_conversation.conversation_id}.json"
    )
    assert not file_path.exists()


def test_backup_compression(temp_persistence_service, sample_conversation):
    """Test that backups are properly compressed."""
    # Save conversation
    temp_persistence_service.save_conversation_with_validation(sample_conversation)

    # Create backup
    backup = temp_persistence_service.create_backup()
    assert backup is not None

    # Verify backup file is compressed
    backup_file = temp_persistence_service.backup_path / f"{backup.backup_id}.json.gz"
    assert backup_file.exists()

    # Verify we can read the compressed content
    with gzip.open(backup_file, "rt", encoding="utf-8") as f:
        backup_data = json.load(f)

    assert "conversations" in backup_data
    assert len(backup_data["conversations"]) == 1
