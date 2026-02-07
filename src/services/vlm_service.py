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

import base64
import io
import json
import os
from typing import Dict, List, Optional

import requests
from PIL import Image

from core.config import get_settings

# Prompt used to guide the VLM's analysis
VLM_PROMPT = (
    "Describe this image in detail. "
    "If it contains text, transcribe it. "
    "If it is a chart or graph, summarize the key trends."
)

# NOTE: Groq frequently updates their model availability.
# Check https://console.groq.com/docs/deprecations for the latest information.
# As of January 2026, llama-3.2-11b-vision-preview has been decommissioned.

# Supported models by provider (verified and working as of January 2026)
SUPPORTED_MODELS = {
    "groq": [
        # Llama 4 Scout - supports vision + tool use
        "meta-llama/llama-4-scout-17b-16e-instruct",
        # Llama 4 Maverick - supports vision + tool use
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        # Llama 3.2 90B - larger model
        "llama-3.2-90b-vision-preview",
    ],
    "mistral": ["pixtral-12b-2409"],
    "local": ["Qwen/Qwen2.5-VL-7B-Instruct"],
}

# Default models for each provider
DEFAULT_MODELS = {
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",  # Updated to Llama 4 Scout
    "mistral": "pixtral-12b-2409",
    "local": "Qwen/Qwen2.5-VL-7B-Instruct",
}


def analyze_extracted_images(base_dir: str, image_paths: List[str]) -> List[Dict]:
    """
    Analyze a list of images using the VLM.

    This function iterates over the provided images, calls the vision model,
    and returns the generated descriptions.

    Args:
        base_dir: The root directory of the current document (context).
        image_paths: List of absolute paths to images requiring analysis.

    Returns:
        A list of results. Each dict contains:
            - 'image': str (filename)
            - 'content_images': str (the generated description)
            - 'method': str (always "vlm")
            - 'is_graph': bool (whether the image appears to be a chart/graph)
    """
    settings = get_settings()

    if not image_paths:
        return []

    MAX_IMAGES_TO_ANALYZE = 10
    MIN_IMAGE_SIZE_KB = 5  # Increased to 5KB to avoid tiny icons/tracking pixels

    # Filter images by size first
    valid_images = []
    for img_path in image_paths:
        if (
            os.path.exists(img_path)
            and os.path.getsize(img_path) > MIN_IMAGE_SIZE_KB * 1024
        ):
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
            print(
                f"  [{count}/{len(images_to_process)}] "
                f"Analyzing: {os.path.basename(img_path)}..."
            )

            # Call remote VLM API
            result = _call_vlm_api(
                img_path,
                settings.vlm.api_url,
                settings.vlm.timeout,
                settings.vlm.model,
                settings.vlm.api_key,
                settings.vlm.provider,
            )

            if result:
                # Copy image to VLM processed folder
                import shutil

                dest_path = os.path.join(vlm_img_dir, os.path.basename(img_path))
                shutil.copy2(img_path, dest_path)

                results.append(
                    {
                        "method": "vlm",
                        "image": os.path.basename(img_path),
                        "content_images": result.get("description", ""),
                        "is_graph": result.get("is_graph", False),
                    }
                )

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


def _validate_image(image_path: str) -> bool:
    """
    Validate that the image file is readable and has valid format.

    Args:
        image_path: Path to the image file

    Returns:
        True if image is valid, False otherwise
    """
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        # If PIL is not available, do basic checks
        if not os.path.exists(image_path):
            return False
        if os.path.getsize(image_path) == 0:
            return False
        # Check file extension
        valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        ext = os.path.splitext(image_path)[1].lower()
        return ext in valid_extensions


def _call_vlm_api(
    image_path: str,
    api_url: str,
    timeout: int = 60,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    provider: str = "groq",
) -> Optional[Dict]:
    """
    Call the remote VLM API to analyze an image.

    Supports Groq, Mistral, and local OpenAI-compatible APIs.

    Args:
        image_path: Path to the image file
        api_url: URL of the VLM API endpoint
        timeout: Request timeout in seconds
        model: Model name to use (optional, will use default if not specified)
        api_key: API key for authentication
        provider: "groq", "mistral", or "local"

    Returns:
        Dictionary with analysis results or None on failure
    """
    try:
        # Validate provider
        if provider not in DEFAULT_MODELS:
            print(
                f"  ⚠️  Unknown provider: {provider}. "
                f"Supported: {', '.join(DEFAULT_MODELS.keys())}"
            )
            return None

        # Validate image before processing
        if not _validate_image(image_path):
            print(
                f"  ⚠️  Invalid or corrupted image file: {os.path.basename(image_path)}"
            )
            return None

        # Determine model to use
        requested_model = model or DEFAULT_MODELS[provider]

        # Validate model for provider
        if requested_model not in SUPPORTED_MODELS.get(provider, []):
            print(f"  ⚠️  Model '{requested_model}' not supported by {provider}.")
            print(f"     Supported models: {', '.join(SUPPORTED_MODELS[provider])}")
            print(f"     Using default: {DEFAULT_MODELS[provider]}")
            requested_model = DEFAULT_MODELS[provider]

        # Standardize image to JPEG using PIL
        # This fixes issues with "invalid image data" for some PNGs/WebPs on Groq
        try:
            with Image.open(image_path) as img:
                # Convert to RGB (handling RGBA transparency)
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")

                # Check dimensions (filter out tiny images < 50x50)
                width, height = img.size
                if width < 50 or height < 50:
                    print(f"  ⚠️  Image too small ({width}x{height}), skip analysis")
                    return None

                # Save to in-memory JPEG
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                image_bytes = buf.getvalue()

                # Encode the sanitized JPEG data
                image_data = base64.b64encode(image_bytes).decode("utf-8")
                ext = "jpeg"  # Force extension to jpeg

        except Exception as e:
            print(f"  ⚠️  Failed to process image {os.path.basename(image_path)}: {e}")
            return None

        # Validate base64 encoding
        if not image_data or len(image_data) < 100:
            print("  ⚠️  Image encoding failed or file too small")
            return None

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
                        "text": (
                            "Describe this image in detail. "
                            "If it contains text, transcribe it. "
                            "If it's a chart or graph, explain what data it shows."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/{ext};base64,{image_data}"},
                    },
                ],
            }
        ]

        # Prepare payload (all providers use OpenAI-compatible format)
        payload = {"model": requested_model, "messages": messages, "max_tokens": 1024}

        # Make API request
        response = requests.post(
            api_url, json=payload, timeout=timeout, headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            # Extract content from response
            content = data["choices"][0]["message"]["content"]

            return {
                "description": content,
                "is_graph": "chart" in content.lower() or "graph" in content.lower(),
            }
        else:
            error_msg = response.text
            print(f"  ⚠️  VLM API returned status {response.status_code}: {error_msg}")
            return None

    except requests.exceptions.Timeout:
        print(f"  ⚠️  VLM API request timed out after {timeout}s")
        return None
    except requests.exceptions.ConnectionError:
        print(f"  ⚠️  Could not connect to VLM API at {api_url}")
        return None
    except Exception as e:
        print(f"  ⚠️  VLM API error: {e}")
        return None


def analyze_single_image(image_path: str) -> Optional[Dict]:
    """
    Analyze a single image using the VLM API.

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary with description and analysis, or None on failure
    """
    settings = get_settings()

    return _call_vlm_api(
        image_path,
        settings.vlm.api_url,
        settings.vlm.timeout,
        settings.vlm.model,
        settings.vlm.api_key,
        settings.vlm.provider,
    )
