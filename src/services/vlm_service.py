"""
VLM (Vision Language Model) Service
VLM Service (Vision Language Model) 👁️‍🗨️
=======================================
This service interacts with Vision Language Models to provide descriptions of images 
that could not be reliably processed by OCR.

Workflow:
---------
1. **Filtering**: Receive images where OCR confidence was low.
2. **Analysis**: Send image + prompt to the VLM (running locally or remotely).
3. **Synthesis**: Return a descriptive caption or summary of the visual content.

Usage:
------
It is primarily called by the `document_pipeline` when `run_ocr_on_images` indicates
failure or low confidence.
"""

import os
import json
import base64
import requests
from core.config import get_settings
from typing import Dict, List

# Prompt used to guide the VLM's analysis
VLM_PROMPT = "Describe this image in detail. If it contains text, transcribe it. If it is a chart or graph, summarize the key trends."

# Supported models by provider (verified and working)
SUPPORTED_MODELS = {
    "groq": [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct"
    ],
    "mistral": [
        "pixtral-12b-2409"
    ],
    "local": [
        "Qwen/Qwen2.5-VL-7B-Instruct"
    ]
}

# Default models for each provider
DEFAULT_MODELS = {
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",
    "mistral": "pixtral-12b-2409",
    "local": "Qwen/Qwen2.5-VL-7B-Instruct"
}


def analyze_extracted_images(base_dir, image_paths):
    """
    Analyze a list of images using the VLM.
    
    This function iterates over the provided images, calls the vision model,
    and returns the generated descriptions.
    
    Args:
        base_dir (str): The root directory of the current document (context).
        image_paths (list): List of absolute paths to images requiring analysis.
    
    Returns:
        list[dict]: A list of results. Each dict contains:
            - 'image': str (filename)
            - 'content_images': str (the generated description)
    """
    settings = get_settings()
    
    if not image_paths:
        return []
    
    MAX_IMAGES_TO_ANALYZE = 10
    MIN_IMAGE_SIZE_KB = 1  # Lowered to 1KB to ensure small but valid images are processed
    
    # Filter images by size first
    valid_images = []
    for img_path in image_paths:
        if os.path.exists(img_path) and os.path.getsize(img_path) > MIN_IMAGE_SIZE_KB * 1024:
            valid_images.append(img_path)
    
    # Sort by size (descending) - assume larger images are more important
    valid_images.sort(key=os.path.getsize, reverse=True)
    
    # Take top N
    images_to_process = valid_images[:MAX_IMAGES_TO_ANALYZE]
    
    if not images_to_process:
        print("ℹ️  No significant images found to analyze (skipped small icons/logos)")
        return []
    
    print(f"\n👁️  Analyzing top {len(images_to_process)} images with VLM...")
    
    # Create directory for VLM processed images
    vlm_img_dir = os.path.join(base_dir, "images", "vlm_processed")
    os.makedirs(vlm_img_dir, exist_ok=True)
    
    results = []
    count = 0
    
    for img_path in images_to_process:
        try:
            count += 1
            print(f"  [{count}/{len(images_to_process)}] Analyzing: {os.path.basename(img_path)}...")
            
            # Call remote VLM API
            result = _call_vlm_api(
                img_path,
                settings.vlm.api_url,
                settings.vlm.timeout,
                settings.vlm.model,
                settings.vlm.api_key,
                settings.vlm.provider
            )
            
            if result:
                # Copy image to VLM processed folder
                import shutil
                dest_path = os.path.join(vlm_img_dir, os.path.basename(img_path))
                shutil.copy2(img_path, dest_path)
                
                results.append({
                    "method": "vlm",
                    "image": os.path.basename(img_path),
                    "content_images": result.get("description", ""),
                    "is_graph": result.get("is_graph", False)
                })
                
        except Exception as e:
            print(f"  ⚠️  Failed to analyze {os.path.basename(img_path)}: {e}")
    
    # Save results
    if results:
        out_path = os.path.join(base_dir, "images", "analysis.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"✅ VLM Analysis saved for {len(results)} images")
    
    return results


def _call_vlm_api(image_path: str, api_url: str, timeout: int = 60, 
                  model: str = None, api_key: str = None, 
                  provider: str = "groq") -> Dict:
    """
    Call the remote VLM API to analyze an image.
    
    Supports Groq, Mistral, and local OpenAI-compatible APIs.
    
    Args:
        image_path: Path to the image file
        api_url: URL of the VLM API endpoint
        timeout: Request timeout in seconds
        model: Model name to use
        api_key: API key for authentication
        provider: "groq", "mistral", or "local"
    
    Returns:
        Dictionary with analysis results or None on failure
    """
    try:
        # Validate provider
        if provider not in DEFAULT_MODELS:
            print(f"  ⚠️  Unknown provider: {provider}")
            return None
        
        # Determine model to use
        requested_model = model or DEFAULT_MODELS[provider]
        
        # Validate model for provider
        if provider in SUPPORTED_MODELS and requested_model not in SUPPORTED_MODELS[provider]:
            print(f"  ⚠️  Model '{requested_model}' not supported by {provider}.")
            print(f"     Supported models: {', '.join(SUPPORTED_MODELS[provider])}")
            print(f"     Using default: {DEFAULT_MODELS[provider]}")
            requested_model = DEFAULT_MODELS[provider]
        
        # Read and encode image as base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Determine image type
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        if ext == "jpg":
            ext = "jpeg"
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Common message structure for all providers
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image in detail. If it contains text, transcribe it. If it's a chart or graph, explain what data it shows."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{ext};base64,{image_data}"
                        }
                    }
                ]
            }
        ]
        
        # Prepare payload (all providers use OpenAI-compatible format)
        payload = {
            "model": requested_model,
            "messages": messages,
            "max_tokens": 1024
        }
        
        # Make API request
        response = requests.post(
            api_url,
            json=payload,
            timeout=timeout,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            # Extract content from response
            content = data["choices"][0]["message"]["content"]
            
            return {
                "description": content,
                "is_graph": "chart" in content.lower() or "graph" in content.lower()
            }
        else:
            print(f"  ⚠️  VLM API returned status {response.status_code}: {response.text}")
            return None
    
    except requests.exceptions.Timeout:
        print(f"  ⚠️  VLM API request timed out")
        return None
    except requests.exceptions.ConnectionError:
        print(f"  ⚠️  Could not connect to VLM API at {api_url}")
        return None
    except Exception as e:
        print(f"  ⚠️  VLM API error: {e}")
        return None


def analyze_single_image(image_path: str) -> Dict:
    """
    Analyze a single image using the VLM API.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Dictionary with description and analysis
    """
    settings = get_settings()
    
    return _call_vlm_api(
        image_path,
        settings.vlm.api_url,
        settings.vlm.timeout,
        settings.vlm.model,
        settings.vlm.api_key,
        settings.vlm.provider
    )