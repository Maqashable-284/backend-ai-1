"""
Scoop AI Core Engine Components (v2.0)
======================================

This package contains the unified conversation engine that replaces
the fragile dual-architecture of v1.0.

Components:
- types: Shared dataclasses and enums
- response_buffer: Thread-safe response accumulation
- tool_executor: Explicit context tool execution
- function_loop: Multi-round function calling logic
- thinking_manager: Thinking UI strategy controller
- engine: Main ConversationEngine

Design Principles:
1. Single implementation for both /chat and /chat/stream
2. No thought-as-text fallbacks (Option D eliminated)
3. Explicit parameter passing (no ContextVar magic)
4. Fail-fast with one retry on empty responses
"""

from .types import (
    ResponseMode,
    RoundResult,
    RequestContext,
    ConversationResult,
    FunctionCall,
    RoundOutput,
    LoopState,
    EngineConfig,
    ErrorResponse,
)
from .response_buffer import ResponseBuffer, BufferState
from .tool_executor import ToolExecutor
from .function_loop import FunctionCallingLoop, EmptyResponseError
from .thinking_manager import (
    ThinkingManager,
    ThinkingStrategy,
    ThinkingEvent,
    create_thinking_manager,
)
from .engine import (
    ConversationEngine,
    ConversationEngineConfig,
    SSEEvent,
    create_conversation_engine,
)

__all__ = [
    # Types
    "ResponseMode",
    "RoundResult",
    "RequestContext",
    "ConversationResult",
    "FunctionCall",
    "RoundOutput",
    "LoopState",
    "EngineConfig",
    "ErrorResponse",
    # Components
    "ResponseBuffer",
    "BufferState",
    "ToolExecutor",
    "FunctionCallingLoop",
    "EmptyResponseError",
    # Thinking Manager
    "ThinkingManager",
    "ThinkingStrategy",
    "ThinkingEvent",
    "create_thinking_manager",
    # Engine
    "ConversationEngine",
    "ConversationEngineConfig",
    "SSEEvent",
    "create_conversation_engine",
]
