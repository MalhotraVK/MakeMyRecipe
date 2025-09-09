"""Chat and conversation data models."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(
        ..., description="Role of the message sender (user, assistant, system)"
    )
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the message was created",
    )


class ChatRequest(BaseModel):
    """Request model for sending a chat message."""

    message: str = Field(..., description="The user's message")
    conversation_id: Optional[str] = Field(
        None, description="ID of existing conversation"
    )
    user_id: str = Field(..., description="ID of the user sending the message")


class ChatResponse(BaseModel):
    """Response model for chat messages."""

    message: str = Field(..., description="The assistant's response")
    conversation_id: str = Field(..., description="ID of the conversation")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the response was generated",
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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the conversation was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the conversation was last updated",
    )

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        message = ChatMessage(role=role, content=content)
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)


class ConversationList(BaseModel):
    """List of conversations for a user."""

    conversations: List[Conversation] = Field(
        default_factory=list, description="List of conversations"
    )
    total: int = Field(0, description="Total number of conversations")


class WebSocketMessage(BaseModel):
    """WebSocket message model."""

    type: str = Field(..., description="Type of message (chat, error, status)")
    data: dict = Field(..., description="Message data")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the message was sent",
    )
