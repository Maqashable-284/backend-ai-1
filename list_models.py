#!/usr/bin/env python3
"""
List all available Gemini models for the given API key.
"""

from google import genai

API_KEY = "AIzaSyDuoZXwt2ftBicxjawl4V8BBXI-v--_e60"

def list_models():
    client = genai.Client(api_key=API_KEY)
    
    print("=" * 70)
    print("📋 Available Gemini Models")
    print("=" * 70)
    
    models = client.models.list()
    
    # Filter for generation models
    gen_models = []
    for model in models:
        if 'gemini' in model.name.lower():
            gen_models.append(model)
    
    # Sort by name
    gen_models.sort(key=lambda x: x.name)
    
    print(f"\n🔢 Total Gemini models: {len(gen_models)}\n")
    
    for model in gen_models:
        name = model.name.replace("models/", "")
        desc = getattr(model, 'description', '')[:60] if hasattr(model, 'description') else ''
        
        # Check for thinking support
        thinking = "🧠" if "2.5" in name else ""
        
        print(f"  {thinking} {name}")
    
    print("\n" + "=" * 70)
    print("🧠 = Supports Thinking API (gemini-2.5-*)")
    print("=" * 70)

if __name__ == "__main__":
    list_models()
