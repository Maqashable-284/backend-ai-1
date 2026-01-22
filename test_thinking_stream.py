#!/usr/bin/env python3
"""
Gemini HIGH Thinking Stream Test
================================
Tests if Gemini 3.0 Flash returns thoughts SEQUENTIALLY during streaming.

Usage: python test_thinking_stream.py
"""

import asyncio
import time
from google import genai
from google.genai import types

# API Key (from user)
API_KEY = "AIzaSyDuoZXwt2ftBicxjawl4V8BBXI-v--_e60"

async def test_thinking_stream():
    """Test HIGH thinking level with streaming."""
    
    print("=" * 60)
    print("🧪 Gemini HIGH Thinking Stream Test")
    print("=" * 60)
    
    # Initialize client
    client = genai.Client(api_key=API_KEY)
    
    # Configure HIGH thinking (budget in tokens - higher = more thinking)
    # gemini-2.5-flash default budget, set high for more reasoning
    thinking_config = types.ThinkingConfig(
        thinking_budget=8192,  # High thinking budget
        include_thoughts=True
    )
    
    config = types.GenerateContentConfig(
        thinking_config=thinking_config,
        temperature=0.7,
    )
    
    # Test query (complex question to trigger thinking)
    query = "რომელი პროტეინი ჯობია მოხუცი ადამიანისთვის, რომელსაც თირკმლის პრობლემა აქვს?"
    
    print(f"\n📝 Query: {query}")
    print("\n⏱️  Streaming response (timestamps):\n")
    
    start_time = time.time()
    thought_count = 0
    text_count = 0
    
    try:
        # Use streaming with gemini-2.5-flash (supports thinking!)
        async for chunk in await client.aio.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=query,
            config=config
        ):
            elapsed = time.time() - start_time
            
            # Check each part in the response
            if chunk.candidates:
                for candidate in chunk.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            # Check if this is a thought
                            if hasattr(part, 'thought') and part.thought:
                                thought_count += 1
                                print(f"[{elapsed:.2f}s] 🧠 THOUGHT #{thought_count}:")
                                print(f"           {part.text[:100]}..." if len(part.text) > 100 else f"           {part.text}")
                                print()
                            elif hasattr(part, 'text') and part.text:
                                text_count += 1
                                snippet = part.text[:80].replace('\n', ' ')
                                print(f"[{elapsed:.2f}s] 📝 TEXT: {snippet}...")
                                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("📊 Results Summary:")
    print("=" * 60)
    print(f"   Total thoughts received: {thought_count}")
    print(f"   Total text chunks: {text_count}")
    print(f"   Total time: {total_time:.2f}s")
    print()
    
    if thought_count > 0:
        print("✅ SUCCESS: Thoughts are streaming!")
        print("   → Implementation is viable")
    else:
        print("⚠️  WARNING: No thoughts received")
        print("   → Check if model supports thinking or try different query")

if __name__ == "__main__":
    asyncio.run(test_thinking_stream())
