
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
    
    # Base64 for a 1x1 red pixel
    small_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKwMjqAAAAAElFTkSuQmCC"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Attempt 1: Standard URL format (what failed before, but confirming identical setup)
    print("Test 1: Standard Data URI scheme")
    payload1 = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe image"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{small_image_b64}"
                        }
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload1)
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error: {response.text}")
        else:
            print("Success!")
    except Exception as e:
        print(e)
        
    print("-" * 20)
    
    # Attempt 2: Just the base64 string, no data URI prefix
    print("Test 2: Raw Base64 string (no data:image/... prefix)")
    payload2 = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe image"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": small_image_b64  # Try just the base64
                        }
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload2)
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error: {response.text}")
        else:
            print("Success!")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_groq_vision()
