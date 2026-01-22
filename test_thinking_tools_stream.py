#!/usr/bin/env python3
"""
Test: Thinking + Function Calling + Streaming Together
Does Gemini 3 Flash support all three at once?
"""

import asyncio
import time
from google import genai
from google.genai import types

API_KEY = "AIzaSyDuoZXwt2ftBicxjawl4V8BBXI-v--_e60"

# Simple test tool
def search_products(query: str) -> dict:
    """Search products by query"""
    return {"products": [{"name": "Test Protein", "price": 50}], "count": 1}

async def test_thinking_tools_streaming():
    """Test all three together."""
    
    print("=" * 70)
    print("🧪 Test: Thinking + Function Calling + Streaming")
    print("=" * 70)
    
    client = genai.Client(api_key=API_KEY)
    
    # Create thinking config
    thinking_config = types.ThinkingConfig(
        thinking_budget=4096,
        include_thoughts=True
    )
    
    # Configure with tools AND thinking
    config = types.GenerateContentConfig(
        thinking_config=thinking_config,
        tools=[search_products],  # Pass function directly
        temperature=0.7,
    )
    
    # Create chat
    chat = client.aio.chats.create(
        model="gemini-3-flash-preview",
        config=config
    )
    
    query = "რომელი პროტეინი გირჩევ?"
    print(f"\n📝 Query: {query}")
    print("\n⏱️  Streaming with send_message_stream():\n")
    
    start = time.time()
    thought_count = 0
    text_count = 0
    fc_count = 0
    
    try:
        async for chunk in await chat.send_message_stream(query):
            elapsed = time.time() - start
            
            # Check candidates
            if hasattr(chunk, 'candidates') and chunk.candidates:
                for candidate in chunk.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            # Thought?
                            if hasattr(part, 'thought') and part.thought:
                                thought_count += 1
                                text = part.text[:60] if part.text else ""
                                print(f"[{elapsed:.2f}s] 🧠 THOUGHT #{thought_count}: {text}...")
                            # Function call?
                            elif hasattr(part, 'function_call') and part.function_call:
                                fc_count += 1
                                print(f"[{elapsed:.2f}s] 🔧 FUNCTION_CALL #{fc_count}: {part.function_call.name}")
                            # Text?
                            elif hasattr(part, 'text') and part.text:
                                text_count += 1
                                if text_count <= 3:
                                    print(f"[{elapsed:.2f}s] 📝 TEXT #{text_count}: {part.text[:50]}...")
                                    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    total = time.time() - start
    print(f"\n{'=' * 70}")
    print(f"📊 Results:")
    print(f"   🧠 Thoughts: {thought_count}")
    print(f"   🔧 Function Calls: {fc_count}")
    print(f"   📝 Text Chunks: {text_count}")
    print(f"   ⏱️  Time: {total:.2f}s")
    
    if thought_count > 0 and text_count > 0:
        print("\n✅ SUCCESS: Thinking + Streaming work together!")
    else:
        print("\n⚠️ Warning: Missing thoughts or text")

if __name__ == "__main__":
    asyncio.run(test_thinking_tools_streaming())
