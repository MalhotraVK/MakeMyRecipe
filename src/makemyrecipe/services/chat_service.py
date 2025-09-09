"""Chat service for handling conversation logic."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.config import settings
from ..core.logging import get_logger
from ..models.chat import (
    ChatMessage,
    Conversation,
    ConversationSearchQuery,
    ConversationSearchResult,
)
from .conversation_persistence import conversation_persistence

logger = get_logger(__name__)


class ChatService:
    """Service for managing chat conversations."""

    def __init__(self) -> None:
        """Initialize the chat service."""
        self.storage_path = Path(settings.conversation_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._conversations: Dict[str, Conversation] = {}
        self._load_conversations()

    def _load_conversations(self) -> None:
        """Load conversations from storage using the persistence service."""
        try:
            for file_path in self.storage_path.glob("*.json"):
                if file_path.name.startswith("backup_"):
                    continue

                conversation_id = file_path.stem
                conversation = (
                    conversation_persistence.load_conversation_with_validation(
                        conversation_id
                    )
                )
                if conversation:
                    self._conversations[conversation.conversation_id] = conversation
                else:
                    logger.warning(f"Failed to load conversation {conversation_id}")

            logger.info(f"Loaded {len(self._conversations)} conversations from storage")
        except Exception as e:
            logger.error(f"Error loading conversations: {e}")

    def _save_conversation(self, conversation: Conversation) -> bool:
        """Save a conversation to storage using the persistence service."""
        success = conversation_persistence.save_conversation_with_validation(
            conversation
        )
        if success:
            logger.debug(f"Saved conversation {conversation.conversation_id}")
        else:
            logger.error(f"Failed to save conversation {conversation.conversation_id}")
        return success

    def create_conversation(
        self, user_id: str, system_prompt: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            user_id=user_id,
            system_prompt=system_prompt
            or Conversation.model_fields["system_prompt"].default,
        )
        self._conversations[conversation.conversation_id] = conversation
        self._save_conversation(conversation)
        logger.info(
            f"Created new conversation {conversation.conversation_id} "
            f"for user {user_id}"
        )
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self._conversations.get(conversation_id)

    def get_user_conversations(
        self, user_id: str, limit: Optional[int] = None
    ) -> List[Conversation]:
        """Get all conversations for a user."""
        user_conversations = [
            conv for conv in self._conversations.values() if conv.user_id == user_id
        ]
        # Sort by updated_at descending
        user_conversations.sort(key=lambda x: x.updated_at, reverse=True)

        if limit:
            user_conversations = user_conversations[:limit]

        return user_conversations

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        parent_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Conversation]:
        """Add a message to a conversation."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return None

        message = conversation.add_message(role, content, parent_message_id, metadata)
        if self._save_conversation(conversation):
            logger.debug(f"Added {role} message to conversation {conversation_id}")
            return conversation
        else:
            # Remove the message if save failed
            conversation.messages.pop()
            return None

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        if conversation_id not in self._conversations:
            return False

        try:
            # Remove from memory
            del self._conversations[conversation_id]

            # Remove from storage
            file_path = self.storage_path / f"{conversation_id}.json"
            if file_path.exists():
                file_path.unlink()

            logger.info(f"Deleted conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            return False

    def get_conversation_messages(self, conversation_id: str) -> List[ChatMessage]:
        """Get messages from a conversation."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        return conversation.messages

    def search_conversations(
        self, query: ConversationSearchQuery
    ) -> List[ConversationSearchResult]:
        """Search conversations using the persistence service."""
        return conversation_persistence.search_conversations(query)

    def create_backup(self, user_id: Optional[str] = None) -> Optional[str]:
        """Create a backup of conversations."""
        backup = conversation_persistence.create_backup(user_id)
        return backup.backup_id if backup else None

    def restore_from_backup(
        self, backup_id: str, user_id: Optional[str] = None
    ) -> bool:
        """Restore conversations from backup."""
        success = conversation_persistence.restore_from_backup(backup_id, user_id)
        if success:
            # Reload conversations after restore
            self._load_conversations()
        return success

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return conversation_persistence.get_storage_stats()

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Clean up old backup files."""
        return conversation_persistence.cleanup_old_backups(keep_count)

    def update_conversation_metadata(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        cuisine_preferences: Optional[List[str]] = None,
        dietary_restrictions: Optional[List[str]] = None,
    ) -> Optional[Conversation]:
        """Update conversation metadata."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        if title is not None:
            conversation.metadata.title = title
        if tags is not None:
            conversation.metadata.tags = tags
        if cuisine_preferences is not None:
            conversation.metadata.cuisine_preferences = cuisine_preferences
        if dietary_restrictions is not None:
            conversation.metadata.dietary_restrictions = dietary_restrictions

        conversation.updated_at = datetime.now(timezone.utc)

        if self._save_conversation(conversation):
            return conversation
        return None


# Global chat service instance
chat_service = ChatService()
