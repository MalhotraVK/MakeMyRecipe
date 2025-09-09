"""WebSocket routes for real-time chat."""

import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from ...core.logging import get_logger
from ...models.chat import WebSocketMessage
from ...services.chat_service import chat_service
from ...services.llm_service import llm_service

logger = get_logger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}

    async def connect(
        self, websocket: WebSocket, connection_id: str, user_id: str
    ) -> None:
        """Accept a WebSocket connection."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)

        logger.info(
            f"WebSocket connection {connection_id} established for user {user_id}"
        )

    def disconnect(self, connection_id: str, user_id: str) -> None:
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        logger.info(
            f"WebSocket connection {connection_id} disconnected for user {user_id}"
        )

    async def send_personal_message(self, message: str, connection_id: str) -> None:
        """Send a message to a specific connection."""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.error(
                        f"Error sending message to connection {connection_id}: {e}"
                    )

    async def send_user_message(self, message: str, user_id: str) -> None:
        """Send a message to all connections for a user."""
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id].copy():
                await self.send_personal_message(message, connection_id)


manager = ConnectionManager()


@router.websocket("/ws/chat/{user_id}")
async def websocket_chat_endpoint(websocket: WebSocket, user_id: str) -> None:
    """WebSocket endpoint for real-time chat."""
    connection_id = f"{user_id}_{id(websocket)}"

    await manager.connect(websocket, connection_id, user_id)

    try:
        # Send welcome message
        welcome_message = WebSocketMessage(
            type="status",
            data={
                "message": "Connected to MakeMyRecipe chat",
                "user_id": user_id,
                "connection_id": connection_id,
            },
        )
        await manager.send_personal_message(
            welcome_message.model_dump_json(), connection_id
        )

        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                message_type = message_data.get("type", "chat")

                if message_type == "chat":
                    await handle_chat_message(message_data, user_id, connection_id)
                elif message_type == "ping":
                    await handle_ping(connection_id)
                else:
                    await send_error_message(
                        f"Unknown message type: {message_type}", connection_id
                    )

            except json.JSONDecodeError:
                await send_error_message("Invalid JSON format", connection_id)
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await send_error_message("Error processing message", connection_id)

    except WebSocketDisconnect:
        manager.disconnect(connection_id, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(connection_id, user_id)


async def handle_chat_message(
    message_data: dict, user_id: str, connection_id: str
) -> None:
    """Handle a chat message from WebSocket."""
    try:
        user_message = message_data.get("message", "")
        conversation_id = message_data.get("conversation_id")

        if not user_message.strip():
            await send_error_message("Message cannot be empty", connection_id)
            return

        # Get or create conversation
        conversation = None
        if conversation_id:
            conversation = chat_service.get_conversation(conversation_id)
            if not conversation:
                await send_error_message("Conversation not found", connection_id)
                return
        else:
            conversation = chat_service.create_conversation(user_id)
            conversation_id = conversation.conversation_id

        # Add user message
        chat_service.add_message(conversation_id, "user", user_message)

        # Send user message confirmation
        user_msg_response = WebSocketMessage(
            type="user_message",
            data={
                "message": user_message,
                "conversation_id": conversation_id,
                "role": "user",
            },
        )
        await manager.send_personal_message(
            user_msg_response.model_dump_json(), connection_id
        )

        # Generate LLM response
        response_content = await llm_service.generate_response(
            conversation.messages, conversation.system_prompt
        )

        # Add assistant response
        chat_service.add_message(conversation_id, "assistant", response_content)

        # Send assistant response
        assistant_msg_response = WebSocketMessage(
            type="assistant_message",
            data={
                "message": response_content,
                "conversation_id": conversation_id,
                "role": "assistant",
            },
        )
        await manager.send_personal_message(
            assistant_msg_response.model_dump_json(), connection_id
        )

    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        await send_error_message("Error processing chat message", connection_id)


async def handle_ping(connection_id: str) -> None:
    """Handle a ping message."""
    pong_message = WebSocketMessage(type="pong", data={"message": "pong"})
    await manager.send_personal_message(pong_message.model_dump_json(), connection_id)


async def send_error_message(error: str, connection_id: str) -> None:
    """Send an error message to a connection."""
    error_message = WebSocketMessage(type="error", data={"error": error})
    await manager.send_personal_message(error_message.model_dump_json(), connection_id)
