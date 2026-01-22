"""
Scoop AI Thinking Manager (v2.0)
================================

Controls the "Thinking UI" experience during streaming responses.

This module replaces the complex "Simulated Thinking" approach from v1.0
with a clean, strategy-based pattern.

v1.0 Problems:
- 100+ lines of hardcoded Georgian "thinking steps"
- SDK Bug #4090: ThinkingConfig + streaming + tools = empty text
- Complex logic scattered across chat_stream function

v2.0 Solution:
- Strategy pattern with pluggable implementations
- NONE (default): No thinking UI, fastest response
- SIMPLE_LOADER: Single "იტვირთება..." message
- NATIVE: Future-proof for when SDK bug is fixed

Design Principle: Decouple UX presentation from core logic.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# THINKING STRATEGY ENUM
# =============================================================================

class ThinkingStrategy(Enum):
    """
    Strategy for displaying thinking UI to users.

    NONE: No thinking UI (fastest, most reliable)
    SIMPLE_LOADER: Static Georgian loading messages
    NATIVE: Use SDK's thinking tokens (when bug #4090 is fixed)
    """
    NONE = "none"
    SIMPLE_LOADER = "simple_loader"
    NATIVE = "native"


# =============================================================================
# PREDEFINED THINKING MESSAGES (Georgian)
# =============================================================================

# Simple loader messages
SIMPLE_LOADER_MESSAGES = [
    "ვფიქრობ...",
    "ვეძებ...",
    "ვამუშავებ...",
]

# Category-specific thinking messages for enhanced UX
CATEGORY_THINKING_MESSAGES: Dict[str, List[str]] = {
    "search": [
        "ვეძებ პროდუქტებს...",
        "ვაანალიზებ არჩევანს...",
    ],
    "recommendation": [
        "ვაფასებ თქვენს მოთხოვნებს...",
        "ვამზადებ რეკომენდაციას...",
    ],
    "general": [
        "ვფიქრობ...",
        "ვამზადებ პასუხს...",
    ],
    "profile": [
        "ვამოწმებ თქვენს პროფილს...",
    ],
}

# Keywords for detecting message intent
INTENT_KEYWORDS: Dict[str, List[str]] = {
    "search": ["ძებნა", "მოძებნე", "რომელი", "რა ღირს", "პროტეინ", "კრეატინ", "ვიტამინ"],
    "recommendation": ["რეკომენდაცია", "ჯობია", "ურჩევ", "შესაფერის", "საუკეთესო"],
    "profile": ["პროფილი", "ალერგია", "მიზანი", "წონა", "სიმაღლე"],
}


# =============================================================================
# THINKING EVENT
# =============================================================================

@dataclass
class ThinkingEvent:
    """
    A single thinking event to be streamed to the user.

    Attributes:
        content: The thinking message to display
        step: Step number (for multi-step thinking)
        is_final: Whether this is the last thinking step
    """
    content: str
    step: int = 0
    is_final: bool = False

    def to_sse_data(self) -> Dict[str, Any]:
        """Convert to SSE data format."""
        return {
            "type": "thinking",
            "content": self.content,
            "step": self.step,
            "is_final": self.is_final,
        }


# =============================================================================
# THINKING MANAGER
# =============================================================================

class ThinkingManager:
    """
    Manages thinking UI during streaming responses.

    REPLACES: The complex "Simulated Thinking" logic in v1.0's chat_stream:
    - get_simulated_thinking_steps()
    - predict_query_complexity()
    - Manual step yielding with delays

    USAGE:
        manager = ThinkingManager(strategy=ThinkingStrategy.SIMPLE_LOADER)

        # At stream start
        for event in manager.get_initial_events(user_message):
            yield event.to_sse_data()

        # When processing thoughts from SDK (NATIVE mode)
        if thought_part:
            event = manager.process_thought_part(thought_part)
            if event:
                yield event.to_sse_data()

        # Mark completion
        manager.mark_complete()
    """

    def __init__(
        self,
        strategy: ThinkingStrategy = ThinkingStrategy.SIMPLE_LOADER,
        custom_messages: Optional[List[str]] = None,
    ):
        """
        Initialize ThinkingManager.

        Args:
            strategy: Thinking UI strategy to use
            custom_messages: Optional custom thinking messages
        """
        self.strategy = strategy
        self.custom_messages = custom_messages

        # State tracking
        self._step_count = 0
        self._is_complete = False
        self._thought_buffer: List[str] = []

        logger.debug(f"ThinkingManager initialized: strategy={strategy.value}")

    # =========================================================================
    # INITIAL EVENTS
    # =========================================================================

    def get_initial_events(
        self,
        user_message: str,
        include_delay_hint: bool = True,
    ) -> List[ThinkingEvent]:
        """
        Get initial thinking events to show at stream start.

        Called before Gemini API call to give immediate user feedback.

        Args:
            user_message: The user's message (for intent detection)
            include_delay_hint: Whether events should include delay hints

        Returns:
            List of ThinkingEvent objects
        """
        if self.strategy == ThinkingStrategy.NONE:
            return []

        if self.strategy == ThinkingStrategy.SIMPLE_LOADER:
            return self._get_simple_loader_events(user_message)

        if self.strategy == ThinkingStrategy.NATIVE:
            # In NATIVE mode, we don't emit initial events
            # We wait for actual thought parts from the SDK
            return []

        return []

    def _get_simple_loader_events(self, user_message: str) -> List[ThinkingEvent]:
        """
        Get simple loader events based on detected intent.

        Args:
            user_message: User's message for intent detection

        Returns:
            List of ThinkingEvent objects
        """
        # Detect intent from message
        intent = self._detect_intent(user_message)

        # Get appropriate messages
        messages = CATEGORY_THINKING_MESSAGES.get(
            intent,
            CATEGORY_THINKING_MESSAGES["general"]
        )

        # Use custom messages if provided
        if self.custom_messages:
            messages = self.custom_messages

        events = []
        for i, msg in enumerate(messages):
            self._step_count += 1
            events.append(ThinkingEvent(
                content=msg,
                step=self._step_count,
                is_final=(i == len(messages) - 1) and self.strategy != ThinkingStrategy.NATIVE,
            ))

        return events

    def _detect_intent(self, message: str) -> str:
        """
        Detect message intent from keywords.

        Args:
            message: User message

        Returns:
            Intent category string
        """
        message_lower = message.lower()

        for intent, keywords in INTENT_KEYWORDS.items():
            if any(kw in message_lower for kw in keywords):
                return intent

        return "general"

    # =========================================================================
    # NATIVE THOUGHT PROCESSING
    # =========================================================================

    def process_thought_part(self, part: Any) -> Optional[ThinkingEvent]:
        """
        Process a thought part from Gemini SDK response.

        Used in NATIVE mode to relay actual AI thoughts to the user.

        Args:
            part: A part object from Gemini response

        Returns:
            ThinkingEvent if part is a thought, None otherwise
        """
        if self.strategy != ThinkingStrategy.NATIVE:
            return None

        # Check if part is a thought
        if not hasattr(part, 'thought') or not part.thought:
            return None

        thought_text = getattr(part, 'text', '') or ''
        if not thought_text.strip():
            return None

        # Buffer and track thoughts
        self._thought_buffer.append(thought_text)
        self._step_count += 1

        logger.debug(f"Native thought received: {thought_text[:50]}...")

        return ThinkingEvent(
            content=thought_text,
            step=self._step_count,
            is_final=False,
        )

    # =========================================================================
    # FUNCTION CALL EVENTS
    # =========================================================================

    def get_function_call_event(self, function_name: str) -> Optional[ThinkingEvent]:
        """
        Get a thinking event for a function call.

        Provides user feedback when AI is executing tools.

        Args:
            function_name: Name of the function being called

        Returns:
            ThinkingEvent or None
        """
        if self.strategy == ThinkingStrategy.NONE:
            return None

        # Map function names to Georgian messages
        messages = {
            "search_products": "ვეძებ პროდუქტებს...",
            "get_user_profile": "ვამოწმებ პროფილს...",
            "update_user_profile": "ვინახავ მონაცემებს...",
            "get_product_details": "ვიღებ დეტალებს...",
        }

        message = messages.get(function_name, f"ვასრულებ: {function_name}...")
        self._step_count += 1

        return ThinkingEvent(
            content=message,
            step=self._step_count,
            is_final=False,
        )

    def get_retry_event(self, product_count: int) -> ThinkingEvent:
        """
        Get a thinking event for retry scenario.

        Called when texts=0 but products found - triggers retry.

        Args:
            product_count: Number of products found

        Returns:
            ThinkingEvent
        """
        self._step_count += 1

        return ThinkingEvent(
            content=f"ნაპოვნია {product_count} პროდუქტი, ვამზადებ რეკომენდაციას...",
            step=self._step_count,
            is_final=False,
        )

    # =========================================================================
    # COMPLETION
    # =========================================================================

    def get_completion_event(self) -> Optional[ThinkingEvent]:
        """
        Get final thinking event to mark thinking complete.

        Returns:
            Final ThinkingEvent or None
        """
        if self.strategy == ThinkingStrategy.NONE:
            return None

        if self._is_complete:
            return None

        self._is_complete = True
        self._step_count += 1

        return ThinkingEvent(
            content="მზადაა!",
            step=self._step_count,
            is_final=True,
        )

    def mark_complete(self) -> None:
        """Mark thinking as complete."""
        self._is_complete = True

    # =========================================================================
    # STATE ACCESS
    # =========================================================================

    @property
    def is_complete(self) -> bool:
        """Check if thinking is complete."""
        return self._is_complete

    @property
    def step_count(self) -> int:
        """Get current step count."""
        return self._step_count

    @property
    def thought_buffer(self) -> List[str]:
        """Get accumulated thoughts (NATIVE mode only)."""
        return self._thought_buffer.copy()

    def reset(self) -> None:
        """Reset manager state for reuse."""
        self._step_count = 0
        self._is_complete = False
        self._thought_buffer = []


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_thinking_manager(
    strategy: Optional[str] = None,
    custom_messages: Optional[List[str]] = None,
) -> ThinkingManager:
    """
    Factory function to create ThinkingManager with settings.

    Args:
        strategy: Strategy name ("none", "simple_loader", "native")
        custom_messages: Optional custom thinking messages

    Returns:
        Configured ThinkingManager
    """
    from config import settings

    # Default to SIMPLE_LOADER for best UX
    # NONE is used only when thinking UI is explicitly disabled
    default_strategy = ThinkingStrategy.SIMPLE_LOADER

    if strategy:
        try:
            thinking_strategy = ThinkingStrategy(strategy.lower())
        except ValueError:
            logger.warning(f"Unknown thinking strategy: {strategy}, using default")
            thinking_strategy = default_strategy
    else:
        thinking_strategy = default_strategy

    return ThinkingManager(
        strategy=thinking_strategy,
        custom_messages=custom_messages,
    )


# =============================================================================
# ASYNC GENERATOR HELPER
# =============================================================================

async def thinking_event_generator(
    manager: ThinkingManager,
    user_message: str,
    delay_seconds: float = 0.3,
) -> AsyncIterator[ThinkingEvent]:
    """
    Async generator for thinking events with delays.

    Used for streaming initial thinking events with animation effect.

    Args:
        manager: ThinkingManager instance
        user_message: User's message
        delay_seconds: Delay between events

    Yields:
        ThinkingEvent objects
    """
    import asyncio

    events = manager.get_initial_events(user_message)

    for event in events:
        yield event
        if delay_seconds > 0 and not event.is_final:
            await asyncio.sleep(delay_seconds)
