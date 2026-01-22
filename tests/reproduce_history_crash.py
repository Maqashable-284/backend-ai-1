
import asyncio
import logging
from google.genai import types
from google.genai.types import Part, UserContent, ModelContent
from app.adapters.gemini_adapter import GeminiAdapter, GeminiConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_bson_to_sdk_history():
    """
    Test that bson_to_sdk_history correctly reconstructs function calls and responses.
    Specifically checks that function_response parts are assigned the 'user' role.
    """
    logger.info("Starting test_bson_to_sdk_history...")
    
    # 1. Simulate BSON history from MongoDB
    # Scenario: 
    # Turn 1 (User): "Hello"
    # Turn 2 (Model): Function Call (search_products)
    # Turn 3 (User/Function): Function Response (products found)
    
    mock_bson_history = [
        # Message 1: User Text
        {
            "role": "user",
            "parts": [{"text": "Hello"}]
        },
        # Message 2: Model Function Call
        {
            "role": "model",
            "parts": [
                {
                    "function_call": {
                        "name": "search_products",
                        "args": {"query": "protein"}
                    }
                }
            ]
        },
        # Message 3: Function Response (This is the critical part that often fails)
        # In BSON, this might be stored with role="user" or "function", 
        # but key is that it MUST be correctly parsed back into a Part with function_response.
        {
            "role": "user",  # SDK expects function responses to be from 'user' (or tool)
            "parts": [
                {
                    "function_response": {
                        "name": "search_products",
                        "response": {"products": ["Product A"]}
                    }
                }
            ]
        }
    ]

    adapter = GeminiAdapter(api_key="fake_key_for_parsing_test")
    
    # 2. Run conversion
    sdk_history = adapter.bson_to_sdk_history(mock_bson_history)
    
    # 3. Verify results
    logger.info(f"Construted SDK History length: {len(sdk_history)}")
    
    # Check Message 1
    assert len(sdk_history) >= 1
    assert isinstance(sdk_history[0], UserContent)
    assert sdk_history[0].parts[0].text == "Hello"
    logger.info("✅ Message 1 (Text) passed")
    
    # Check Message 2
    if len(sdk_history) < 2:
        logger.error("❌ Message 2 missing! Function Call was likely ignored.")
        return False
        
    assert isinstance(sdk_history[1], ModelContent)
    # Note: Accessing function_call depends on how the SDK structure exposes it, 
    # but initially we just check if the part exists and is not text.
    part2 = sdk_history[1].parts[0]
    if not hasattr(part2, 'function_call') or not part2.function_call:
        logger.error(f"❌ Message 2 missing function_call! Got: {part2}")
        return False
        
    logger.info("✅ Message 2 (Function Call) passed")
    
    # Check Message 3
    if len(sdk_history) < 3:
        logger.error("❌ Message 3 missing! Function Response was likely ignored.")
        return False
    
    msg3 = sdk_history[2]
    # Function response should be attributed to User in connectionless chat or specific role
    assert isinstance(msg3, UserContent) or msg3.role == 'user'
    
    part3 = msg3.parts[0]
    if not hasattr(part3, 'function_response') or not part3.function_response:
        logger.error(f"❌ Message 3 missing function_response! Got: {part3}")
        return False

    logger.info("✅ Message 3 (Function Response) passed")
    
    return True

if __name__ == "__main__":
    try:
        success = test_bson_to_sdk_history()
        if success:
            print("TEST PASSED: History reconstructed correctly.")
            exit(0)
        else:
            print("TEST FAILED: History reconstruction incomplete.")
            exit(1)
    except Exception as e:
        print(f"TEST FAILED with Exception: {e}")
        exit(1)
