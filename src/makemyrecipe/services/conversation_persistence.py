"""Advanced conversation persistence service with backup/recovery/search."""

import gzip
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.config import settings
from ..core.logging import get_logger
from ..models.chat import (
    ChatMessage,
    Conversation,
    ConversationBackup,
    ConversationSearchQuery,
    ConversationSearchResult,
)

logger = get_logger(__name__)


class ConversationPersistenceService:
    """Advanced service for conversation persistence with backup/recovery/search."""

    def __init__(self) -> None:
        """Initialize the persistence service."""
        self.storage_path = Path(settings.conversation_storage_path)
        self.backup_path = self.storage_path / "backups"
        self.temp_path = self.storage_path / "temp"

        # Create directories
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)

    def calculate_checksum(self, data: str) -> str:
        """Calculate SHA-256 checksum for data integrity."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def calculate_conversation_checksum(self, conversation: Conversation) -> str:
        """Calculate checksum for a conversation object."""
        # Create a copy and remove checksum
        temp_conversation = conversation.model_copy()
        temp_conversation.checksum = None

        # Serialize with consistent formatting
        data = temp_conversation.model_dump()
        json_data = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
        return self.calculate_checksum(json_data)

    def validate_conversation_data(
        self, data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate conversation data structure."""
        errors = []

        # Check required fields
        required_fields = [
            "conversation_id",
            "user_id",
            "messages",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate messages structure
        if "messages" in data and isinstance(data["messages"], list):
            for i, message in enumerate(data["messages"]):
                if not isinstance(message, dict):
                    errors.append(f"Message {i} is not a dictionary")
                    continue

                msg_required = ["role", "content", "timestamp"]
                for field in msg_required:
                    if field not in message:
                        errors.append(f"Message {i} missing field: {field}")

                # Validate role
                if "role" in message and message["role"] not in {
                    "user",
                    "assistant",
                    "system",
                }:
                    errors.append(f"Message {i} has invalid role: {message['role']}")

        # Validate version if present
        if "version" in data and not isinstance(data["version"], int):
            errors.append("Version must be an integer")

        return len(errors) == 0, errors

    def save_conversation_with_validation(self, conversation: Conversation) -> bool:
        """Save conversation with data validation and integrity checks."""
        try:
            # Calculate and store checksum
            checksum = self.calculate_conversation_checksum(conversation)
            conversation.checksum = checksum

            # Serialize conversation with checksum
            data = conversation.model_dump()
            json_data = json.dumps(data, indent=2, default=str)

            # Validate data structure
            is_valid, errors = self.validate_conversation_data(data)
            if not is_valid:
                logger.error(f"Conversation validation failed: {errors}")
                return False

            # Write to temporary file first
            temp_file = self.temp_path / f"{conversation.conversation_id}.json.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(json_data)

            # Atomic move to final location
            final_file = self.storage_path / f"{conversation.conversation_id}.json"
            shutil.move(str(temp_file), str(final_file))

            logger.debug(
                f"Saved conversation {conversation.conversation_id} "
                f"with checksum {checksum[:8]}..."
            )
            return True

        except Exception as e:
            logger.error(
                f"Error saving conversation {conversation.conversation_id}: {e}"
            )
            return False

    def load_conversation_with_validation(
        self, conversation_id: str
    ) -> Optional[Conversation]:
        """Load conversation with data validation and integrity checks."""
        try:
            file_path = self.storage_path / f"{conversation_id}.json"
            if not file_path.exists():
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate data structure
            is_valid, errors = self.validate_conversation_data(data)
            if not is_valid:
                logger.error(
                    f"Loaded conversation {conversation_id} failed validation: {errors}"
                )
                # Try to recover from backup
                return self._recover_from_backup(conversation_id)

            # Ensure timezone-aware datetimes
            self._ensure_timezone_aware(data)

            # Create conversation object
            conversation = Conversation(**data)

            # Verify checksum if present
            if conversation.checksum:
                temp_checksum = conversation.checksum
                calculated_checksum = self.calculate_conversation_checksum(conversation)

                if calculated_checksum != temp_checksum:
                    logger.warning(
                        f"Checksum mismatch for conversation {conversation_id}: "
                        f"expected {temp_checksum[:8]}..., "
                        f"got {calculated_checksum[:8]}..."
                    )
                    # Try to recover from backup
                    backup_conversation = self._recover_from_backup(conversation_id)
                    if backup_conversation:
                        return backup_conversation
                    else:
                        # No backup available, return None for corrupted data
                        return None

            return conversation

        except Exception as e:
            logger.error(f"Error loading conversation {conversation_id}: {e}")
            # Try to recover from backup
            return self._recover_from_backup(conversation_id)

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

    def create_backup(
        self, user_id: Optional[str] = None
    ) -> Optional[ConversationBackup]:
        """Create a backup of conversations."""
        try:
            backup_id = f"backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            if user_id:
                backup_id += f"_{user_id}"

            backup_file = self.backup_path / f"{backup_id}.json.gz"

            # Collect conversations to backup
            conversations = []
            total_size = 0

            for file_path in self.storage_path.glob("*.json"):
                if file_path.name.startswith("backup_"):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Filter by user_id if specified
                    if user_id and data.get("user_id") != user_id:
                        continue

                    conversations.append(data)
                    total_size += file_path.stat().st_size

                except Exception as e:
                    logger.warning(f"Skipping corrupted file {file_path}: {e}")

            if not conversations:
                logger.info("No conversations to backup")
                return None

            # Create backup data
            backup_data = {
                "backup_id": backup_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "conversations": conversations,
                "metadata": {
                    "user_id": user_id,
                    "conversation_count": len(conversations),
                    "total_size": total_size,
                },
            }

            # Serialize and compress
            json_data = json.dumps(backup_data, default=str)
            checksum = self.calculate_checksum(json_data)

            with gzip.open(backup_file, "wt", encoding="utf-8") as f:
                f.write(json_data)

            # Create backup metadata
            backup = ConversationBackup(
                backup_id=backup_id,
                conversation_count=len(conversations),
                total_size=total_size,
                checksum=checksum,
            )

            logger.info(
                f"Created backup {backup_id} with {len(conversations)} conversations"
            )
            return backup

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None

    def restore_from_backup(
        self, backup_id: str, user_id: Optional[str] = None
    ) -> bool:
        """Restore conversations from backup."""
        try:
            backup_file = self.backup_path / f"{backup_id}.json.gz"
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_id}")
                return False

            # Load and decompress backup
            with gzip.open(backup_file, "rt", encoding="utf-8") as f:
                backup_data = json.load(f)

            # Verify backup integrity
            conversations = backup_data.get("conversations", [])
            if not conversations:
                logger.error(f"No conversations found in backup {backup_id}")
                return False

            restored_count = 0
            for conv_data in conversations:
                try:
                    # Filter by user_id if specified
                    if user_id and conv_data.get("user_id") != user_id:
                        continue

                    # Validate conversation data
                    is_valid, errors = self.validate_conversation_data(conv_data)
                    if not is_valid:
                        logger.warning(f"Skipping invalid conversation: {errors}")
                        continue

                    # Ensure timezone-aware datetimes
                    self._ensure_timezone_aware(conv_data)

                    # Create and save conversation
                    conversation = Conversation(**conv_data)
                    if self.save_conversation_with_validation(conversation):
                        restored_count += 1

                except Exception as e:
                    logger.warning(f"Error restoring conversation: {e}")

            logger.info(
                f"Restored {restored_count} conversations from backup {backup_id}"
            )
            return restored_count > 0

        except Exception as e:
            logger.error(f"Error restoring from backup {backup_id}: {e}")
            return False

    def _recover_from_backup(self, conversation_id: str) -> Optional[Conversation]:
        """Try to recover a specific conversation from the latest backup."""
        try:
            # Find the most recent backup
            backup_files = sorted(
                self.backup_path.glob("backup_*.json.gz"), reverse=True
            )

            for backup_file in backup_files:
                try:
                    with gzip.open(backup_file, "rt", encoding="utf-8") as f:
                        backup_data = json.load(f)

                    conversations = backup_data.get("conversations", [])
                    for conv_data in conversations:
                        if conv_data.get("conversation_id") == conversation_id:
                            # Validate and restore
                            is_valid, errors = self.validate_conversation_data(
                                conv_data
                            )
                            if is_valid:
                                self._ensure_timezone_aware(conv_data)
                                logger.info(
                                    f"Recovered conversation {conversation_id} "
                                    f"from backup"
                                )
                                return Conversation(**conv_data)

                except Exception as e:
                    logger.warning(f"Error reading backup {backup_file}: {e}")

            logger.error(
                f"Could not recover conversation {conversation_id} from any backup"
            )
            return None

        except Exception as e:
            logger.error(
                f"Error during recovery of conversation {conversation_id}: {e}"
            )
            return None

    def search_conversations(
        self, query: ConversationSearchQuery
    ) -> List[ConversationSearchResult]:
        """Search conversations based on query parameters."""
        try:
            results = []

            for file_path in self.storage_path.glob("*.json"):
                if file_path.name.startswith("backup_"):
                    continue

                try:
                    conversation = self.load_conversation_with_validation(
                        file_path.stem
                    )
                    if not conversation:
                        continue

                    # Filter by user_id
                    if conversation.user_id != query.user_id:
                        continue

                    # Apply filters
                    if not self._matches_filters(conversation, query):
                        continue

                    # Calculate relevance score
                    score, matching_messages = self._calculate_relevance(
                        conversation, query
                    )
                    if score > 0:
                        results.append(
                            ConversationSearchResult(
                                conversation=conversation,
                                relevance_score=score,
                                matching_messages=matching_messages,
                            )
                        )

                except Exception as e:
                    logger.warning(f"Error processing conversation {file_path}: {e}")

            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)

            # Apply pagination
            start = query.offset
            end = start + query.limit
            return results[start:end]

        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            return []

    def _matches_filters(
        self, conversation: Conversation, query: ConversationSearchQuery
    ) -> bool:
        """Check if conversation matches filter criteria."""
        # Date range filter
        if query.date_from and conversation.created_at < query.date_from:
            return False
        if query.date_to and conversation.created_at > query.date_to:
            return False

        # Tags filter
        if query.tags:
            if not any(tag in conversation.metadata.tags for tag in query.tags):
                return False

        # Cuisine preferences filter
        if query.cuisine_preferences:
            if not any(
                cuisine in conversation.metadata.cuisine_preferences
                for cuisine in query.cuisine_preferences
            ):
                return False

        # Dietary restrictions filter
        if query.dietary_restrictions:
            if not any(
                restriction in conversation.metadata.dietary_restrictions
                for restriction in query.dietary_restrictions
            ):
                return False

        return True

    def _calculate_relevance(
        self, conversation: Conversation, query: ConversationSearchQuery
    ) -> Tuple[float, List[str]]:
        """Calculate relevance score for a conversation."""
        if not query.query:
            return 1.0, []  # No text query, return base score

        score = 0.0
        matching_messages = []
        query_terms = query.query.lower().split()

        # Search in conversation title
        if conversation.metadata.title:
            title_matches = sum(
                1 for term in query_terms if term in conversation.metadata.title.lower()
            )
            score += title_matches * 2.0  # Title matches are weighted higher

        # Search in messages
        for message in conversation.messages:
            content_lower = message.content.lower()
            message_matches = sum(1 for term in query_terms if term in content_lower)
            if message_matches > 0:
                score += message_matches
                matching_messages.append(message.message_id)

        # Search in tags
        for tag in conversation.metadata.tags:
            tag_matches = sum(1 for term in query_terms if term in tag.lower())
            score += tag_matches * 1.5  # Tag matches are weighted higher

        # Normalize score by query length
        if query_terms:
            score = score / len(query_terms)

        return score, matching_messages

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            stats = {
                "total_conversations": 0,
                "total_size": 0,
                "total_messages": 0,
                "backup_count": 0,
                "backup_size": 0,
                "corrupted_files": 0,
            }

            # Count conversation files
            for file_path in self.storage_path.glob("*.json"):
                if file_path.name.startswith("backup_"):
                    continue

                try:
                    stats["total_size"] += file_path.stat().st_size
                    stats["total_conversations"] += 1

                    # Count messages
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if "messages" in data:
                        stats["total_messages"] += len(data["messages"])

                except Exception:
                    stats["corrupted_files"] += 1

            # Count backup files
            for backup_file in self.backup_path.glob("backup_*.json.gz"):
                stats["backup_count"] += 1
                stats["backup_size"] += backup_file.stat().st_size

            return stats

        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Clean up old backup files, keeping only the most recent ones."""
        try:
            backup_files = sorted(
                self.backup_path.glob("backup_*.json.gz"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )

            if len(backup_files) <= keep_count:
                return 0

            removed_count = 0
            for backup_file in backup_files[keep_count:]:
                try:
                    backup_file.unlink()
                    removed_count += 1
                    logger.debug(f"Removed old backup: {backup_file.name}")
                except Exception as e:
                    logger.warning(f"Error removing backup {backup_file}: {e}")

            logger.info(f"Cleaned up {removed_count} old backup files")
            return removed_count

        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
            return 0


# Global persistence service instance
conversation_persistence = ConversationPersistenceService()
