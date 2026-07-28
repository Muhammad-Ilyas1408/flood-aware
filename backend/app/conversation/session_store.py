"""Async-safe in-memory storage for immutable conversation sessions."""

import asyncio
from uuid import UUID, uuid4

from backend.app.conversation.models import ConversationSession, ConversationTurn


class ConversationSessionStore:
    """Own bounded-scope in-memory session storage for FYP v1.0.

    This store deliberately provides no persistence, TTL, or eviction policy.
    Those concerns require an approved production persistence boundary.
    """

    def __init__(self) -> None:
        """Initialize isolated session storage and its asynchronous guard."""
        self._sessions: dict[UUID, ConversationSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(self) -> UUID:
        """Create and return an empty immutable conversation session identifier."""
        session_id = uuid4()
        async with self._lock:
            self._sessions[session_id] = ConversationSession(session_id=session_id)
        return session_id

    async def get_session(self, session_id: UUID) -> ConversationSession | None:
        """Return the immutable session snapshot, if the identifier is known."""
        async with self._lock:
            return self._sessions.get(session_id)

    async def append_turn(
        self, session_id: UUID, turn: ConversationTurn
    ) -> ConversationSession:
        """Append one turn atomically and return the resulting session snapshot."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise ValueError(f"Conversation session {session_id} does not exist.")
            updated = session.model_copy(update={"turns": session.turns + (turn,)})
            self._sessions[session_id] = updated
            return updated
