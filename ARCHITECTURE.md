# Scoop AI v2.0 Architecture

## Overview

Scoop AI v2.0 features a **Unified Conversation Engine** that replaces the legacy dual-architecture approach. This document describes the core components, data flow, and design decisions.

---

## Design Principles

1. **Single Implementation** - Both `/chat` and `/chat/stream` endpoints use the same `ConversationEngine`
2. **Explicit Parameter Passing** - No ContextVar magic; all context passed explicitly
3. **Fail-Fast with Retry** - Clear error states instead of fallback heuristics
4. **State Encapsulation** - All response state managed by `ResponseBuffer`
5. **Testability** - Components are isolated and independently testable

---

## Component Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         v2.0 COMPONENT HIERARCHY                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  app/                                                                        │
│  ├── core/                          # Core engine components                 │
│  │   ├── __init__.py                # Clean exports                         │
│  │   ├── types.py                   # Shared dataclasses & enums            │
│  │   ├── engine.py                  # ConversationEngine                    │
│  │   ├── function_loop.py           # FunctionCallingLoop                   │
│  │   ├── response_buffer.py         # ResponseBuffer                        │
│  │   ├── thinking_manager.py        # ThinkingManager                       │
│  │   └── tool_executor.py           # ToolExecutor                          │
│  │                                                                           │
│  ├── adapters/                      # External service adapters              │
│  │   ├── gemini_adapter.py          # Gemini SDK wrapper                    │
│  │   └── mongo_adapter.py           # MongoDB operations                    │
│  │                                                                           │
│  ├── reasoning/                     # Query orchestration layer              │
│  │   ├── query_analyzer.py          # Constraint extraction                 │
│  │   ├── constraint_search.py       # Pre-search logic                      │
│  │   └── context_injector.py        # Message enhancement                   │
│  │                                                                           │
│  └── tools/                         # Tool execution                         │
│      └── user_tools.py              # Explicit user_id parameter            │
│                                                                              │
│  main.py                            # Thin controller (~1,700 lines)        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. ConversationEngine (`app/core/engine.py`)

The main entry point for all chat interactions.

```python
class ConversationEngine:
    """
    Unified engine for handling chat conversations.
    
    Methods:
        process_message() - Sync mode for /chat endpoint
        stream_message()  - Async generator for /chat/stream endpoint
    """
```

**Responsibilities:**
- Initialize context (user profile, history)
- Orchestrate the function calling loop
- Assemble the final response
- Persist conversation history

### 2. FunctionCallingLoop (`app/core/function_loop.py`)

Handles multi-round Gemini interactions with retry logic.

```python
class FunctionCallingLoop:
    """
    Multi-round function calling executor.
    
    Retry Policy:
        1. If texts=0 AND products found → retry once with summary prompt
        2. If still texts=0 → raise EmptyResponseError
        3. No Option D fallback (using thoughts as text)
    """
```

**Key Features:**
- Maximum 3 rounds of function calling
- Deduplication of search queries
- Explicit retry trigger on empty response
- `EmptyResponseError` for predictable failure states

### 3. ResponseBuffer (`app/core/response_buffer.py`)

Thread-safe accumulator for response components.

```python
class ResponseBuffer:
    """
    Thread-safe response accumulator.
    
    Features:
        - Atomic text operations
        - Product deduplication (by id, _id, product_id)
        - Single TIP extraction point
        - Immutable snapshots for SSE
    """
```

**Eliminates:**
- 15+ scattered state variables
- Race conditions in concurrent access
- Multiple TIP extraction calls

### 4. ThinkingManager (`app/core/thinking_manager.py`)

Strategy-based thinking UI controller.

```python
class ThinkingStrategy(Enum):
    NONE = "none"           # No thinking UI (fastest)
    SIMPLE_LOADER = "simple_loader"  # Georgian loading messages
    NATIVE = "native"       # SDK thinking tokens (future)
```

**Replaced:**
- `get_simulated_thinking_steps()` (~160 lines)
- `translate_thought()` (~40 lines)
- `THOUGHT_CACHE` dictionary (~60 lines)

### 5. ToolExecutor (`app/core/tool_executor.py`)

Explicit context passing for tool functions.

```python
class ToolExecutor:
    def __init__(self, user_id: str, user_profile: dict = None):
        self.user_id = user_id
        self.user_profile = user_profile  # Pre-cached
```

**Key Change:** `user_id` is passed explicitly to all tool functions, eliminating ContextVar propagation issues.

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REQUEST FLOW (v2.0)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. REQUEST ARRIVES                                                          │
│     ┌─────────────────────────────────────────────────────────────────────┐ │
│     │ POST /chat/stream                                                   │ │
│     │ { user_id: "user123", message: "მინდა პროტეინი 100 ლარამდე" }       │ │
│     └─────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  2. CONVERSATION ENGINE                                                      │
│     ┌─────────────────────────────────────────────────────────────────────┐ │
│     │ ConversationEngine.stream_message()                                 │ │
│     │   1. Load user profile (MongoAdapter)                               │ │
│     │   2. Load conversation history                                      │ │
│     │   3. Create ToolExecutor with explicit user_id                      │ │
│     │   4. Initialize ResponseBuffer                                      │ │
│     │   5. Initialize ThinkingManager (SIMPLE_LOADER)                     │ │
│     └─────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  3. FUNCTION CALLING LOOP                                                    │
│     ┌─────────────────────────────────────────────────────────────────────┐ │
│     │ FunctionCallingLoop.execute()                                       │ │
│     │                                                                     │ │
│     │   Round 1: "მინდა პროტეინი 100 ლარამდე"                             │ │
│     │      → Gemini: FC(search_products, query="პროტეინი", max_price=100) │ │
│     │      → ToolExecutor.execute() with explicit user_id                 │ │
│     │      → Products found: 5                                            │ │
│     │                                                                     │ │
│     │   Round 2: [function_response]                                      │ │
│     │      → Gemini: Text response with product recommendations           │ │
│     │      → RoundResult.COMPLETE                                         │ │
│     └─────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  4. RESPONSE ASSEMBLY                                                        │
│     ┌─────────────────────────────────────────────────────────────────────┐ │
│     │ ResponseBuffer operations:                                          │ │
│     │   - set_text(gemini_response)                                       │ │
│     │   - add_products(found_products)  # With deduplication              │ │
│     │   - extract_and_set_tip()         # Single extraction               │ │
│     │   - parse_quick_replies()                                           │ │
│     └─────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  5. SSE STREAMING                                                            │
│     ┌─────────────────────────────────────────────────────────────────────┐ │
│     │ yield SSEEvent(type="thinking", content="ვეძებ პროდუქტებს...")      │ │
│     │ yield SSEEvent(type="text", content="აი რა ვიპოვე...")              │ │
│     │ yield SSEEvent(type="products", content=[...])                      │ │
│     │ yield SSEEvent(type="tip", content="პრაქტიკული რჩევა...")           │ │
│     │ yield SSEEvent(type="quick_replies", content=[...])                 │ │
│     │ yield SSEEvent(type="done")                                         │ │
│     └─────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Error Handling Strategy

### texts=0 Problem (Empty Response)

**v1.0 Approach (Removed):**
```
texts=0?
  → Find longest thought
  → Truncate to 800 chars
  → Use as response (PROBLEMATIC!)
```

**v2.0 Approach:**
```
texts=0?
  → Has products? → Retry once with summary prompt
  → Still empty? → Raise EmptyResponseError
  → Frontend shows: "გთხოვთ სცადოთ ხელახლა"
```

### Error Response Structure

```python
ERROR_RESPONSES = {
    "empty_response": ErrorResponse(
        error_code="empty_response",
        message_georgian="პასუხის გენერირება ვერ მოხერხდა.",
        can_retry=True,
        suggestion="სცადეთ უფრო კონკრეტული კითხვა"
    ),
    "timeout": ErrorResponse(
        error_code="timeout",
        message_georgian="მოთხოვნას ძალიან დიდი დრო დასჭირდა.",
        can_retry=True,
    ),
}
```

---

## Removed Components (v1.0 → v2.0)

| Component | Reason for Removal |
|-----------|-------------------|
| `get_simulated_thinking_steps()` | Replaced by ThinkingManager |
| `THOUGHT_CACHE` dictionary | No thought translation needed |
| `translate_thought()` | No thought translation needed |
| Option D fallback logic | Replaced by retry + fail-fast |
| `_current_user_id` ContextVar | Replaced by explicit parameters |
| Speculative search | Removed for stability |
| 737-line `chat_stream` function | Replaced by ConversationEngine |

---

## Metrics

| Metric | v1.0 | v2.0 | Change |
|--------|------|------|--------|
| main.py lines | ~3,162 | ~1,710 | **-46%** |
| Fallback code paths | 7+ | 2 | **-71%** |
| State variables | 15+ | 0 (encapsulated) | **-100%** |
| ContextVar usage | 3 places | 0 | **-100%** |
| Unit tests | ~30 | 186 | **+520%** |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run core component tests
pytest tests/core/ -v

# Expected: 186+ tests passing
```

---

## See Also

- [CONTEXT.md](./CONTEXT.md) - Full development history
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment instructions
- [README.md](./README.md) - Quick start guide
