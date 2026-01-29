
import requests
import json
import base64
import io
from PIL import Image
from core.config import get_settings

def test_groq_vision_v5():
    settings = get_settings()
    api_key = settings.vlm.api_key
    api_url = settings.vlm.api_url
    model = "meta-llama/llama-4-scout-17b-16e-instruct"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    print("Generating 100x100 blank JPEG...")
    try:
        img = Image.new('RGB', (100, 100), color='white')
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=80)
        img_bytes = buf.getvalue()
        b64_str = base64.b64encode(img_bytes).decode('utf-8')
        
        print(f"Base64 length: {len(b64_str)}")
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "What color is this?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_str}"}}
                    ]
                }
            ]
        }
        
        print(f"Test A: Sending 100x100 image (Base64) to {model}...")
        r = requests.post(api_url, headers=headers, json=payload)
        if r.status_code == 200:
             print("✅ Success (Base64)!")
             print(json.dumps(r.json(), indent=2))
        else:
             print(f"❌ Failed (Base64): {r.text}")

    except Exception as e:
        print(f"Error generating image: {e}")

    print("-" * 20)

    # Test B: Reliable Public URL
    print("Test B: Sending Public URL (placehold.co)...")
    payload_b = {
        "model": model,
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "Read the text in this image."},
                    {"type": "image_url", "image_url": {"url": "https://placehold.co/600x400/png"}}
                ]
            }
        ]
    }
    
    try:
        r = requests.post(api_url, headers=headers, json=payload_b)
        if r.status_code == 200:
             print("✅ Success (URL)!")
             print(json.dumps(r.json(), indent=2))
        else:
             print(f"❌ Failed (URL): {r.text}")
             
    except Exception as e: print(e)

if __name__ == "__main__":
    test_groq_vision_v5()
