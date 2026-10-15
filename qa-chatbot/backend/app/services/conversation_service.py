"""Conversation Management Service.

Maintains server-side, in-memory conversation history keyed by validated session ID.
Provides concurrency-safe access, turn-based history windowing, and session isolation.

NOTE ON HORIZONTAL SCALING:
This in-memory implementation is intended for single-instance POC deployments.
In-memory history does NOT survive application restarts or container recreation.
For multi-replica deployments behind a load balancer, replace this in-memory store
with a distributed storage backend (such as Redis or DynamoDB) using the same interface.
"""

import asyncio
from collections import defaultdict
import logging
from typing import Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ConversationService:
    """Manages multi-turn conversation state per session with memory limits."""

    def __init__(self, max_history_turns: int = 10) -> None:
        """Initialize conversation service.

        Args:
            max_history_turns: Maximum conversation turns (user+assistant pairs) to preserve.
        """
        self.max_history_turns = max_history_turns
        # Maps session_id -> list of LangChain BaseMessage objects (HumanMessage, AIMessage)
        self._sessions: dict[str, list[BaseMessage]] = defaultdict(list)
        # Lock to ensure atomic mutation of conversation history under concurrent requests
        self._lock = asyncio.Lock()
        logger.info(
            "ConversationService initialized with max_history_turns=%d",
            self.max_history_turns,
        )

    async def get_history(self, session_id: str) -> list[BaseMessage]:
        """Retrieve a copy of the conversation history for a validated session ID.

        Args:
            session_id: Validated UUID session identifier.

        Returns:
            List of BaseMessage objects belonging strictly to this session.
        """
        async with self._lock:
            # Return a shallow copy of the message list to protect internal state
            return list(self._sessions.get(session_id, []))

    async def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Atomically record a user-assistant dialogue turn and apply history truncation.

        Args:
            session_id: Validated UUID session identifier.
            user_message: Sanitized user input query.
            assistant_message: AI assistant's generated response.
        """
        async with self._lock:
            history = self._sessions[session_id]
            history.append(HumanMessage(content=user_message))
            history.append(AIMessage(content=assistant_message))

            # Apply sliding window: Each turn is 2 messages (1 Human + 1 AI)
            max_messages = self.max_history_turns * 2
            if len(history) > max_messages:
                # Keep the most recent max_messages
                trimmed = history[-max_messages:]
                self._sessions[session_id] = trimmed
                logger.debug(
                    "Session %s history trimmed to %d messages (%d turns)",
                    session_id,
                    len(trimmed),
                    self.max_history_turns,
                )

    async def clear_session(self, session_id: str) -> bool:
        """Remove a session and all its conversation history from memory.

        Args:
            session_id: Validated UUID session identifier.

        Returns:
            True if session existed and was removed, False otherwise.
        """
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info("Cleared conversation session: %s", session_id)
                return True
            return False

    async def get_turn_count(self, session_id: str) -> int:
        """Get the number of completed turns for a given session."""
        async with self._lock:
            return len(self._sessions.get(session_id, [])) // 2

    async def get_active_session_count(self) -> int:
        """Get total number of active sessions in memory."""
        async with self._lock:
            return len(self._sessions)


# Global singleton instance for the service lifecycle within the process
_conversation_service_instance: ConversationService | None = None


def get_conversation_service() -> ConversationService:
    """Dependency provider for ConversationService."""
    global _conversation_service_instance
    if _conversation_service_instance is None:
        settings = get_settings()
        _conversation_service_instance = ConversationService(
            max_history_turns=settings.MAX_HISTORY_TURNS
        )
    return _conversation_service_instance
