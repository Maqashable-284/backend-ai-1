#!/usr/bin/env python3
"""
Test gemini-3-flash-preview thinking support
"""

import asyncio
import time
from google import genai
from google.genai import types

API_KEY = "AIzaSyDuoZXwt2ftBicxjawl4V8BBXI-v--_e60"

async def test_gemini3_thinking():
    """Test gemini-3-flash-preview with thinking config."""
    
    print("=" * 70)
    print("🧪 Testing: gemini-3-flash-preview Thinking Support")
    print("=" * 70)
    
    client = genai.Client(api_key=API_KEY)
    
    # Try with thinking_budget
    thinking_config = types.ThinkingConfig(
        thinking_budget=8192,
        include_thoughts=True
    )
    
    config = types.GenerateContentConfig(
        thinking_config=thinking_config,
        temperature=0.7,
    )
    
    query = "რომელი პროტეინი ჯობია?"
    
    print(f"\n📝 Query: {query}")
    print(f"🔧 Config: thinking_budget=8192, include_thoughts=True")
    print("\n⏱️  Testing streaming...\n")
    
    start_time = time.time()
    thought_count = 0
    text_count = 0
    
    try:
        async for chunk in await client.aio.models.generate_content_stream(
            model="gemini-3-flash-preview",
            contents=query,
            config=config
        ):
            elapsed = time.time() - start_time
            
            if chunk.candidates:
                for candidate in chunk.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'thought') and part.thought:
                                thought_count += 1
                                text = part.text[:80] if part.text else ""
                                print(f"[{elapsed:.2f}s] 🧠 THOUGHT #{thought_count}: {text}...")
                            elif hasattr(part, 'text') and part.text:
                                text_count += 1
                                if text_count <= 3:
                                    snippet = part.text[:60].replace('\n', ' ')
                                    print(f"[{elapsed:.2f}s] 📝 TEXT: {snippet}...")
                                
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Error: {error_msg[:200]}")
        
        if "thinking" in error_msg.lower() or "not supported" in error_msg.lower():
            print("\n⚠️  CONCLUSION: gemini-3-flash-preview does NOT support Thinking API")
        return
    
    total_time = time.time() - start_time
    
    print(f"\n{'=' * 70}")
    print("📊 Results:")
    print(f"   Thoughts: {thought_count}")
    print(f"   Text chunks: {text_count}")
    print(f"   Time: {total_time:.2f}s")
    
    if thought_count > 0:
        print("\n✅ SUCCESS: gemini-3-flash-preview SUPPORTS Thinking!")
    else:
        print("\n⚠️  No thoughts received - model may not support thinking")

if __name__ == "__main__":
    asyncio.run(test_gemini3_thinking())
