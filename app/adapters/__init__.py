"""
Scoop AI Adapter Layer (v2.0)
=============================

This package contains adapters that wrap external services,
providing clean interfaces for the ConversationEngine.

Adapters:
- GeminiAdapter: Wraps Google Gemini SDK calls
- MongoAdapter: Wraps MongoDB operations

Design Principle: Adapters isolate external dependencies,
making the core engine testable with mocks.
"""

from .gemini_adapter import GeminiAdapter
from .mongo_adapter import MongoAdapter

__all__ = [
    "GeminiAdapter",
    "MongoAdapter",
]
