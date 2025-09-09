"""Chat and conversation data models."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    """A single chat message."""

    message_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique message ID"
    )
    role: str = Field(
        ..., description="Role of the message sender (user, assistant, system)"
    )
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the message was created",
    )
    parent_message_id: Optional[str] = Field(
        None, description="ID of parent message for threading"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional message metadata"
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate message role."""
        allowed_roles = {"user", "assistant", "system"}
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of {allowed_roles}")
        return v


class ChatRequest(BaseModel):
    """Request model for sending a chat message."""

    message: str = Field(..., description="The user's message")
    conversation_id: Optional[str] = Field(
        None, description="ID of existing conversation"
    )
    user_id: str = Field(..., description="ID of the user sending the message")


class Citation(BaseModel):
    """Citation model for web search results."""

    title: str = Field(..., description="Title of the cited source")
    url: str = Field(..., description="URL of the cited source")
    snippet: Optional[str] = Field(None, description="Snippet from the source")


class ChatResponse(BaseModel):
    """Response model for chat messages."""

    message: str = Field(..., description="The assistant's response")
    conversation_id: str = Field(..., description="ID of the conversation")
    citations: List[Citation] = Field(
        default_factory=list, description="Citations from web search"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the response was generated",
    )


class ConversationMetadata(BaseModel):
    """Metadata for a conversation."""

    title: Optional[str] = Field(None, description="Conversation title")
    tags: List[str] = Field(default_factory=list, description="Conversation tags")
    language: str = Field("en", description="Conversation language")
    cuisine_preferences: List[str] = Field(
        default_factory=list, description="User's cuisine preferences"
    )
    dietary_restrictions: List[str] = Field(
        default_factory=list, description="User's dietary restrictions"
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata fields"
    )


class Conversation(BaseModel):
    """A conversation containing multiple messages."""

    conversation_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique conversation ID"
    )
    user_id: str = Field(..., description="ID of the user who owns this conversation")
    system_prompt: str = Field(
        default=(
            "You are MakeMyRecipe, an AI assistant specialized in helping users "
            "create delicious recipes. You provide proven recipes with links to "
            "actual pages or YouTube videos, remember user preferences, and offer "
            "personalized cooking suggestions based on available ingredients and "
            "dietary requirements."
        ),
        description="System prompt for the conversation",
    )
    messages: List[ChatMessage] = Field(
        default_factory=list, description="List of messages in the conversation"
    )
    metadata: ConversationMetadata = Field(
        default_factory=ConversationMetadata, description="Conversation metadata"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the conversation was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the conversation was last updated",
    )
    version: int = Field(1, description="Conversation schema version")
    checksum: Optional[str] = Field(None, description="Data integrity checksum")

    def add_message(
        self,
        role: str,
        content: str,
        parent_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Add a message to the conversation."""
        message = ChatMessage(
            role=role,
            content=content,
            parent_message_id=parent_message_id,
            metadata=metadata or {},
        )
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
        return message

    def get_message_by_id(self, message_id: str) -> Optional[ChatMessage]:
        """Get a message by its ID."""
        for message in self.messages:
            if message.message_id == message_id:
                return message
        return None

    def get_thread_messages(
        self, parent_message_id: Optional[str] = None
    ) -> List[ChatMessage]:
        """Get messages in a specific thread."""
        return [
            msg for msg in self.messages if msg.parent_message_id == parent_message_id
        ]

    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.messages)

    def get_size_estimate(self) -> int:
        """Estimate conversation size in bytes."""
        return len(self.model_dump_json())

    @field_validator("version")
    @classmethod
    def validate_version(cls, v):
        """Validate conversation version."""
        if v < 1:
            raise ValueError("Version must be >= 1")
        return v


class ConversationList(BaseModel):
    """List of conversations for a user."""

    conversations: List[Conversation] = Field(
        default_factory=list, description="List of conversations"
    )
    total: int = Field(0, description="Total number of conversations")


class ConversationSearchQuery(BaseModel):
    """Search query for conversations."""

    user_id: str = Field(..., description="User ID to search within")
    query: Optional[str] = Field(None, description="Text search query")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    cuisine_preferences: Optional[List[str]] = Field(
        None, description="Filter by cuisine"
    )
    dietary_restrictions: Optional[List[str]] = Field(
        None, description="Filter by dietary restrictions"
    )
    limit: int = Field(10, description="Maximum results to return")
    offset: int = Field(0, description="Results offset for pagination")


class ConversationSearchResult(BaseModel):
    """Search result for conversations."""

    conversation: Conversation = Field(..., description="Found conversation")
    relevance_score: float = Field(..., description="Search relevance score")
    matching_messages: List[str] = Field(
        default_factory=list, description="IDs of matching messages"
    )


class ConversationBackup(BaseModel):
    """Backup metadata for conversations."""

    backup_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique backup ID"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When backup was created",
    )
    conversation_count: int = Field(
        ..., description="Number of conversations backed up"
    )
    total_size: int = Field(..., description="Total backup size in bytes")
    checksum: str = Field(..., description="Backup integrity checksum")
    compression: str = Field("gzip", description="Compression method used")


class WebSocketMessage(BaseModel):
    """WebSocket message model."""

    type: str = Field(..., description="Type of message (chat, error, status)")
    data: dict = Field(..., description="Message data")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the message was sent",
    )
