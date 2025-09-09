"""Chat API routes."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ...core.logging import get_logger
from ...models.chat import (
    ChatRequest,
    ChatResponse,
    Citation,
    Conversation,
    ConversationList,
)
from ...services.chat_service import chat_service
from ...services.llm_service import llm_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest) -> ChatResponse:
    """Send a chat message and get a response."""
    try:
        # Get or create conversation
        conversation = None
        if request.conversation_id:
            conversation = chat_service.get_conversation(request.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation
            conversation = chat_service.create_conversation(request.user_id)

        # Add user message to conversation
        chat_service.add_message(conversation.conversation_id, "user", request.message)

        # Generate LLM response with citations
        (
            response_content,
            citations_data,
        ) = await llm_service.generate_response_with_citations(
            conversation.messages, conversation.system_prompt
        )

        # Add assistant response to conversation
        chat_service.add_message(
            conversation.conversation_id, "assistant", response_content
        )

        # Convert citations to Citation objects
        citations = [
            Citation(
                title=citation.get("title", "") if citation else "",
                url=citation.get("url", "") if citation else "",
                snippet=citation.get("snippet", "") if citation else "",
            )
            for citation in citations_data
            if citation is not None
        ]

        return ChatResponse(
            message=response_content,
            conversation_id=conversation.conversation_id,
            citations=citations,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations", response_model=ConversationList)
async def get_conversations(
    user_id: str = Query(..., description="User ID to get conversations for"),
    limit: Optional[int] = Query(
        None, description="Maximum number of conversations to return"
    ),
) -> ConversationList:
    """Get conversation history for a user."""
    try:
        conversations = chat_service.get_user_conversations(user_id, limit)
        return ConversationList(conversations=conversations, total=len(conversations))
    except Exception as e:
        logger.error(f"Error getting conversations for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str) -> Conversation:
    """Get a specific conversation by ID."""
    try:
        conversation = chat_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str) -> JSONResponse:
    """Delete a conversation."""
    try:
        success = chat_service.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return JSONResponse(content={"message": "Conversation deleted successfully"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/conversations", response_model=Conversation)
async def create_conversation(
    user_id: str = Query(..., description="User ID for the new conversation"),
    system_prompt: Optional[str] = Query(None, description="Custom system prompt"),
) -> Conversation:
    """Create a new conversation."""
    try:
        conversation = chat_service.create_conversation(user_id, system_prompt)
        return conversation
    except Exception as e:
        logger.error(f"Error creating conversation for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
