
import os
import base64
import requests
import json
from core.config import get_settings

def test_groq_vision():
    settings = get_settings()
    api_key = settings.vlm.api_key
    model = settings.vlm.model
    api_url = settings.vlm.api_url
    
    print(f"Testing Groq Vision API...")
    print(f"URL: {api_url}")
    print(f"Model: {model}")
    print(f"API Key present: {bool(api_key)}")
    
    # Create a simple 1x1 red pixel PNG
    # Base64 for a 1x1 red pixel
    small_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKwMjqAAAAAElFTkSuQmCC"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": "What is in this image?"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{small_image_b64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 100
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Success!")
            print("Response:", json.dumps(response.json(), indent=2))
        else:
            print("❌ Failed!")
            print("Response:", response.text)
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_groq_vision()
