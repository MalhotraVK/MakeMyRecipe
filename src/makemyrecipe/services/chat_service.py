"""Chat service for handling conversation logic."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from ..core.config import settings
from ..core.logging import get_logger
from ..models.chat import ChatMessage, Conversation

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
        """Load conversations from storage."""
        try:
            for file_path in self.storage_path.glob("*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Ensure datetime fields are timezone-aware
                    self._ensure_timezone_aware(data)
                    conversation = Conversation(**data)
                    self._conversations[conversation.conversation_id] = conversation
            logger.info(f"Loaded {len(self._conversations)} conversations from storage")
        except Exception as e:
            logger.error(f"Error loading conversations: {e}")

    def _ensure_timezone_aware(self, data: dict) -> None:
        """Ensure datetime fields are timezone-aware."""
        for field in ["created_at", "updated_at"]:
            if field in data and isinstance(data[field], str):
                dt = datetime.fromisoformat(data[field].replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                data[field] = dt

        # Handle messages
        if "messages" in data:
            for message in data["messages"]:
                if "timestamp" in message and isinstance(message["timestamp"], str):
                    dt = datetime.fromisoformat(
                        message["timestamp"].replace("Z", "+00:00")
                    )
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    message["timestamp"] = dt

    def _save_conversation(self, conversation: Conversation) -> None:
        """Save a conversation to storage."""
        try:
            file_path = self.storage_path / f"{conversation.conversation_id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(conversation.model_dump(), f, indent=2, default=str)
            logger.debug(f"Saved conversation {conversation.conversation_id}")
        except Exception as e:
            logger.error(
                f"Error saving conversation {conversation.conversation_id}: {e}"
            )

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
        self, conversation_id: str, role: str, content: str
    ) -> Optional[Conversation]:
        """Add a message to a conversation."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return None

        conversation.add_message(role, content)
        self._save_conversation(conversation)
        logger.debug(f"Added {role} message to conversation {conversation_id}")
        return conversation

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


# Global chat service instance
chat_service = ChatService()
