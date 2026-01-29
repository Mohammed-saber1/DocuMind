
import requests
import json
from core.config import get_settings

def test_groq_vision_v4():
    settings = get_settings()
    api_key = settings.vlm.api_key
    api_url = settings.vlm.api_url
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Test A: Maverick with Base64
    model_a = "meta-llama/llama-4-maverick-17b-128e-instruct"
    print(f"Test A: {model_a} with Base64")
    
    jpeg_b64 = "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9aAAwDAQACEQAA/wD3IAH/2Q=="
    
    payload_a = {
        "model": model_a,
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "Describe."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{jpeg_b64}"}}
                ]
            }
        ]
    }
    
    try:
        r = requests.post(api_url, headers=headers, json=payload_a)
        if r.status_code == 200:
             print("✅ Success!")
        else:
             print(f"❌ Failed: {r.text}")
    except Exception as e: print(e)
    
    print("-" * 20)

    # Test B: Scout with Public URL
    model_b = "meta-llama/llama-4-scout-17b-16e-instruct"
    print(f"Test B: {model_b} with Public URL")
    
    payload_b = {
        "model": model_b,
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "Describe image."},
                    {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gnome-terminal.png/100px-Gnome-terminal.png"}}
                ]
            }
        ]
    }
    
    try:
        r = requests.post(api_url, headers=headers, json=payload_b)
        if r.status_code == 200:
             print("✅ Success!")
             print(json.dumps(r.json(), indent=2))
        else:
             print(f"❌ Failed: {r.text}")
    except Exception as e: print(e)

if __name__ == "__main__":
    test_groq_vision_v4()
