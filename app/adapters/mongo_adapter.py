"""
Scoop AI MongoDB Adapter (v2.0)
===============================

Wraps MongoDB operations, providing a clean interface for the ConversationEngine.

Key Responsibilities:
1. Load and save conversation history
2. Get and update user profiles
3. Increment user statistics
4. Provide a consistent interface regardless of MongoDB implementation details

Design Principle: The engine should not know about MongoDB internals.
This adapter delegates to ConversationStore/UserStore but provides
a simplified interface focused on engine needs.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.memory.mongo_store import (
    ConversationStore,
    UserStore,
    db_manager,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class MongoConfig:
    """Configuration for MongoAdapter."""
    max_messages_before_prune: int = 100
    max_tokens_before_prune: int = 50000
    default_language: str = "ka"


# =============================================================================
# MONGO ADAPTER
# =============================================================================

class MongoAdapter:
    """
    Adapter for MongoDB operations.

    Provides a clean, engine-focused interface over ConversationStore
    and UserStore. The engine uses this adapter instead of directly
    interacting with MongoDB.

    USAGE:
        adapter = MongoAdapter(config=MongoConfig())

        # Load history
        history, session_id, summary = await adapter.load_history(user_id)

        # Save history
        await adapter.save_history(user_id, session_id, gemini_history)

        # Get user profile
        profile = await adapter.get_user_profile(user_id)

        # Update stats
        await adapter.increment_user_stats(user_id, messages=2)
    """

    def __init__(self, config: Optional[MongoConfig] = None):
        """
        Initialize MongoAdapter.

        Args:
            config: Optional configuration
        """
        self.config = config or MongoConfig()

        # Delegate stores - lazily instantiated
        self._conversation_store: Optional[ConversationStore] = None
        self._user_store: Optional[UserStore] = None

        logger.info(
            f"MongoAdapter initialized: max_messages={self.config.max_messages_before_prune}"
        )

    # =========================================================================
    # PROPERTY ACCESSORS (Lazy initialization)
    # =========================================================================

    @property
    def conversation_store(self) -> ConversationStore:
        """Get or create ConversationStore instance."""
        if self._conversation_store is None:
            self._conversation_store = ConversationStore(
                max_messages=self.config.max_messages_before_prune,
                max_tokens=self.config.max_tokens_before_prune,
            )
        return self._conversation_store

    @property
    def user_store(self) -> UserStore:
        """Get or create UserStore instance."""
        if self._user_store is None:
            self._user_store = UserStore()
        return self._user_store

    # =========================================================================
    # HISTORY OPERATIONS
    # =========================================================================

    async def load_history(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], str, Optional[str]]:
        """
        Load conversation history for a user.

        If session_id is provided, loads that specific session.
        Otherwise, loads the most recent session for the user.

        Args:
            user_id: User identifier
            session_id: Optional session identifier

        Returns:
            tuple: (history_as_bson, session_id, summary)
                - history_as_bson: List of message dicts (BSON format)
                - session_id: Session identifier (created if new)
                - summary: Optional summary of pruned older messages
        """
        try:
            history, sid, summary = await self.conversation_store.load_history(
                user_id=user_id,
                session_id=session_id,
            )

            logger.info(
                f"Loaded history: user={user_id}, session={sid}, "
                f"messages={len(history)}, has_summary={summary is not None}"
            )

            return history, sid, summary

        except Exception as e:
            logger.error(f"Failed to load history for user {user_id}: {e}")
            # Return empty history with new session on error
            import uuid
            new_session_id = f"session_{uuid.uuid4().hex[:12]}"
            return [], new_session_id, None

    async def save_history(
        self,
        user_id: str,
        session_id: str,
        history: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save conversation history.

        Handles automatic pruning when history exceeds limits.
        The history parameter accepts either Gemini SDK Content objects
        or already-converted BSON format.

        Args:
            user_id: User identifier
            session_id: Session identifier
            history: Gemini chat history (SDK Content objects or BSON list)
            metadata: Optional metadata to store with the session

        Returns:
            True if save was successful, False otherwise
        """
        try:
            await self.conversation_store.save_history(
                user_id=user_id,
                session_id=session_id,
                history=history,
                metadata=metadata,
            )

            logger.info(
                f"Saved history: user={user_id}, session={session_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save history for user {user_id}: {e}")
            return False

    async def get_session_history_for_display(
        self,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get formatted message history for frontend display.

        Converts internal BSON format to frontend-friendly format:
        [{"role": "user"|"assistant", "content": "..."}]

        Args:
            session_id: Session identifier

        Returns:
            List of formatted messages
        """
        return await self.conversation_store.get_session_history(session_id)

    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get list of user's recent sessions for sidebar display.

        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries with titles
        """
        return await self.conversation_store.get_user_sessions(user_id, limit)

    async def clear_session(self, session_id: str) -> bool:
        """
        Delete a specific session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted
        """
        return await self.conversation_store.clear_session(session_id)

    # =========================================================================
    # USER PROFILE OPERATIONS
    # =========================================================================

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile for system prompt injection.

        Returns the full profile structure without embeddings,
        suitable for including in LLM context.

        Args:
            user_id: User identifier

        Returns:
            User profile dict or None if not found
        """
        try:
            # Use the enhanced get_full_profile method
            profile = await self.user_store.get_full_profile(user_id)

            if profile:
                logger.debug(f"Loaded profile for user {user_id}")

            return profile

        except Exception as e:
            logger.error(f"Failed to get profile for user {user_id}: {e}")
            return None

    async def get_user_raw(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get raw user document (for advanced operations).

        Args:
            user_id: User identifier

        Returns:
            Raw user document or None
        """
        return await self.user_store.get_user(user_id)

    async def create_or_update_user(
        self,
        user_id: str,
        profile_updates: Optional[Dict[str, Any]] = None,
        stats_updates: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create or update user profile.

        Args:
            user_id: User identifier
            profile_updates: Optional dict of profile field updates
            stats_updates: Optional dict of stats field updates

        Returns:
            Updated user document or None on error
        """
        try:
            return await self.user_store.create_or_update_user(
                user_id=user_id,
                profile_updates=profile_updates,
                stats_updates=stats_updates,
            )
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return None

    async def set_user_name(self, user_id: str, name: str) -> bool:
        """
        Set user's display name.

        Args:
            user_id: User identifier
            name: User's name

        Returns:
            True if successful
        """
        try:
            await self.user_store.set_user_name(user_id, name)
            return True
        except Exception as e:
            logger.error(f"Failed to set name for user {user_id}: {e}")
            return False

    async def add_allergy(self, user_id: str, allergy: str) -> bool:
        """
        Add an allergy to user profile.

        Args:
            user_id: User identifier
            allergy: Allergy name

        Returns:
            True if successful
        """
        try:
            await self.user_store.add_allergy(user_id, allergy)
            return True
        except Exception as e:
            logger.error(f"Failed to add allergy for user {user_id}: {e}")
            return False

    # =========================================================================
    # STATISTICS
    # =========================================================================

    async def increment_user_stats(
        self,
        user_id: str,
        messages: int = 1,
        sessions: int = 0,
    ) -> bool:
        """
        Increment user statistics.

        Args:
            user_id: User identifier
            messages: Number of messages to add
            sessions: Number of sessions to add

        Returns:
            True if successful
        """
        try:
            if messages > 0:
                await self.user_store.increment_stats(user_id, messages=messages)

            if sessions > 0:
                await self.user_store.create_or_update_user(
                    user_id=user_id,
                    stats_updates={"total_sessions": sessions}
                )

            return True

        except Exception as e:
            logger.error(f"Failed to increment stats for user {user_id}: {e}")
            return False

    # =========================================================================
    # EXTENDED PROFILE METHODS (Delegated to UserStore)
    # =========================================================================

    async def update_demographics(
        self,
        user_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """
        Update user demographics (age, gender, occupation).

        Args:
            user_id: User identifier
            updates: Dict with keys: age, gender, occupation, occupation_category

        Returns:
            True if successful
        """
        try:
            return await self.user_store.update_demographics(user_id, updates)
        except Exception as e:
            logger.error(f"Failed to update demographics for user {user_id}: {e}")
            return False

    async def update_physical_stats(
        self,
        user_id: str,
        height: Optional[float] = None,
        body_fat_percent: Optional[float] = None,
    ) -> bool:
        """
        Update physical stats (height, body_fat).

        For weight, use add_weight_entry() for versioned tracking.

        Args:
            user_id: User identifier
            height: Height in cm
            body_fat_percent: Body fat percentage

        Returns:
            True if successful
        """
        try:
            return await self.user_store.update_physical_stats(
                user_id, height, body_fat_percent
            )
        except Exception as e:
            logger.error(f"Failed to update physical stats for user {user_id}: {e}")
            return False

    async def add_weight_entry(
        self,
        user_id: str,
        weight: float,
        note: Optional[str] = None,
    ) -> bool:
        """
        Add weight entry to history (versioned tracking).

        Args:
            user_id: User identifier
            weight: Weight value
            note: Optional note (e.g., "morning", "after workout")

        Returns:
            True if successful
        """
        try:
            return await self.user_store.add_weight_entry(user_id, weight, note)
        except Exception as e:
            logger.error(f"Failed to add weight entry for user {user_id}: {e}")
            return False

    async def update_lifestyle(
        self,
        user_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """
        Update lifestyle fields.

        Args:
            user_id: User identifier
            updates: Dict with keys: workout_frequency, experience_years,
                     sleep_hours, activity_level

        Returns:
            True if successful
        """
        try:
            return await self.user_store.update_lifestyle(user_id, updates)
        except Exception as e:
            logger.error(f"Failed to update lifestyle for user {user_id}: {e}")
            return False

    # =========================================================================
    # SEMANTIC MEMORY METHODS
    # =========================================================================

    async def add_user_fact(
        self,
        user_id: str,
        fact: str,
        embedding: List[float],
        importance_score: float = 0.5,
        source: str = "user_stated",
        is_sensitive: bool = False,
    ) -> Dict[str, Any]:
        """
        Add a semantic fact about the user (with deduplication).

        Args:
            user_id: User identifier
            fact: The fact text (min 10 chars)
            embedding: 768-dim vector
            importance_score: 0.0-1.0
            source: "user_stated" or "inferred"
            is_sensitive: True for sensitive info

        Returns:
            {"status": "added"|"duplicate"|"error", "message": str}
        """
        try:
            return await self.user_store.add_user_fact(
                user_id=user_id,
                fact=fact,
                embedding=embedding,
                importance_score=importance_score,
                source=source,
                is_sensitive=is_sensitive,
            )
        except Exception as e:
            logger.error(f"Failed to add fact for user {user_id}: {e}")
            return {"status": "error", "message": str(e)}

    async def get_relevant_facts(
        self,
        user_id: str,
        query_embedding: List[float],
        limit: int = 5,
        min_similarity: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Get relevant user facts using vector similarity.

        Args:
            user_id: User identifier
            query_embedding: 768-dim query vector
            limit: Max facts to return
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of facts sorted by similarity
        """
        try:
            return await self.user_store.get_relevant_facts(
                user_id=user_id,
                query_embedding=query_embedding,
                limit=limit,
                min_similarity=min_similarity,
            )
        except Exception as e:
            logger.error(f"Failed to get relevant facts for user {user_id}: {e}")
            return []

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    async def health_check(self) -> bool:
        """
        Check MongoDB connection health.

        Returns:
            True if connection is healthy
        """
        try:
            return await db_manager.ping()
        except Exception:
            return False


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_mongo_adapter(
    max_messages: Optional[int] = None,
    max_tokens: Optional[int] = None,
) -> MongoAdapter:
    """
    Factory function to create MongoAdapter with settings.

    Args:
        max_messages: Max messages before pruning
        max_tokens: Max tokens before pruning

    Returns:
        Configured MongoAdapter
    """
    config = MongoConfig()

    if max_messages is not None:
        config.max_messages_before_prune = max_messages
    if max_tokens is not None:
        config.max_tokens_before_prune = max_tokens

    return MongoAdapter(config=config)
