"""OCR service for image-based text extraction using PaddleOCR."""

import json
import logging
import os

# Suppress PaddlePaddle warnings (fscanf: Success [0])
os.environ["GLOG_minloglevel"] = "2"
os.environ["FLAGS_minloglevel"] = "2"

from typing import Dict, List, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Global PaddleOCR instance (Lazy loaded)
_PADDLE_OCR = None


def get_paddle_ocr():
    """Get or initialize the PaddleOCR instance."""
    global _PADDLE_OCR
    if _PADDLE_OCR is None:
        try:
            from paddleocr import PaddleOCR

            from core.config import get_settings

            settings = get_settings()
            use_gpu = settings.ocr.gpu

            # Check compatible devices
            if use_gpu:
                import paddle

                # If compiled with CUDA but no device found, or not compiled with CUDA at all
                if not paddle.device.is_compiled_with_cuda():
                    print(
                        "⚠️ PaddlePaddle is not compiled with CUDA. Forcing use_gpu=False."
                    )
                    use_gpu = False
                elif not paddle.device.get_available_device():
                    print("⚠️ No GPU devices found. Forcing use_gpu=False.")
                    use_gpu = False

            # Initialize PaddleOCR
            # lang='en' default, but it supports multilingual.
            # We can use 'en' or specific configs. PaddleOCR auto-downloads models.
            print(
                f"📦 Initializing PaddleOCR (use_gpu={use_gpu})... This may take a moment."
            )

            try:
                _PADDLE_OCR = PaddleOCR(
                    use_angle_cls=True,
                    lang="en",  # Default language
                    use_gpu=use_gpu,
                    show_log=False,
                )
                print("✅ PaddleOCR initialized")
            except Exception as e:
                if use_gpu:
                    print(f"⚠️ GPU initialization failed: {e}. Falling back to CPU.")
                    _PADDLE_OCR = PaddleOCR(
                        use_angle_cls=True, lang="en", use_gpu=False, show_log=False
                    )
                    print("✅ PaddleOCR initialized (CPU mode)")
                else:
                    raise e
        except ImportError:
            print(
                "❌ PaddleOCR not found. Please install: pip install paddleocr paddlepaddle"
            )
            return None
        except Exception as e:
            print(f"❌ Failed to initialize PaddleOCR: {e}")
            return None
    return _PADDLE_OCR


# Confidence threshold presets
CONFIDENCE_PRESETS = {
    "strict": 0.85,  # Very high quality required
    "standard": 0.70,  # Recommended for most uses
    "lenient": 0.60,  # Accept more OCR results
    "permissive": 0.50,  # Maximum speed
}

OCR_THRESHOLD = CONFIDENCE_PRESETS["standard"]


def extract_text_with_paddle(image_path: str) -> Tuple[str, float]:
    """
    Extract text from an image using PaddleOCR.

    Args:
        image_path: Path to the image file

    Returns:
        tuple: (text, confidence)
    """
    ocr = get_paddle_ocr()
    if not ocr:
        return "", 0.0

    try:
        # Run OCR
        result = ocr.ocr(image_path, cls=True)

        if not result or result[0] is None:
            return "", 0.0

        # Parse result: result = [[[[x1,y1], [x2,y2], ...], ("text", confidence)], ...]
        text_lines = []
        confidences = []

        for line in result[0]:
            text_content = line[1][0]
            confidence = line[1][1]

            text_lines.append(text_content)
            confidences.append(confidence)

        full_text = "\n".join(text_lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return full_text, avg_confidence

    except Exception as e:
        print(f"⚠️ OCR Error processing {os.path.basename(image_path)}: {e}")
        return "", 0.0


def run_ocr_on_images(images: List[str]) -> List[Dict]:
    """
    Process a list of image paths and extract text from them.

    This function iterates through all provided images and attempts to extract text.
    It returns a structured list of results including text, confidence, and metadata.

    Args:
        image_paths (list): List of absolute file paths to images.

    Returns:
        list[dict]: A list of result dictionaries. Each dict contains:
            - 'path': str
            - 'text': str (cleaned)
            - 'confidence': float (0.0 to 1.0)
    """
    results = []
    print(f"🧠 Running OCR on {len(images)} images...")

    # Create directory for OCR processed images
    # NOTE: In a full pipeline context we'd want base_dir, but for now we infer it or leave as is.
    # To keep functional purity, we just process here. The pipeline should handle organizing if needed,
    # or we do it if we can infer parent.

    for img in images:
        # Check if file exists and is not empty
        if not os.path.exists(img) or os.path.getsize(img) == 0:
            continue

        # Optional: Skip tiny images if not already filtered
        if os.path.getsize(img) < 5120:  # < 5KB
            continue

        text, conf = extract_text_with_paddle(img)

        # Save processed image to ocr_processed folder if text found
        if text.strip():
            try:
                base_dir = os.path.dirname(
                    os.path.dirname(img)
                )  # ../images/img.png -> ..
                ocr_img_dir = os.path.join(base_dir, "images", "ocr_processed")
                os.makedirs(ocr_img_dir, exist_ok=True)

                import shutil

                dest_path = os.path.join(ocr_img_dir, os.path.basename(img))
                shutil.copy2(img, dest_path)
            except Exception:
                pass  # Fail silently on file ops to ensure result return

        results.append({"path": img, "text": text.strip(), "confidence": conf})

    return results


async def run_ocr_on_images_async(images: List[str]) -> List[Dict]:
    """
    Async wrapper for OCR processing.

    Offloads the CPU-bound OCR work to a thread pool to avoid
    blocking the event loop. This improves performance when
    processing multiple files concurrently.

    Args:
        images: List of image paths to process

    Returns:
        List of OCR result dictionaries
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_ocr_on_images, images)


def should_use_ocr(confidence: float, text: str, threshold: float = None) -> bool:
    """Check if OCR result is sufficient."""
    threshold = threshold if threshold is not None else OCR_THRESHOLD
    return (confidence >= threshold) and (text and len(text.strip()) > 5)


def maybe_run_ocr(base_dir, images, engine="paddle"):
    """
    Compatibility function for legacy pipeline calls.
    Run OCR on images if the extracted text is insufficient.

    Args:
        base_dir: Base directory containing the text folder
        images: List of image paths to process
        engine: Ignored, kept for compatibility

    Returns:
        tuple: (extracted_text, average_confidence)
    """
    text_path = os.path.join(base_dir, "text", "content.txt")

    if os.path.exists(text_path):
        with open(text_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    else:
        text = ""

    # If we already have enough text, or no images, skip OCR
    if len(text) > 50 or not images:
        return text, 1.0

    # Run OCR
    results = run_ocr_on_images(images)

    ocr_text = [r["text"] for r in results if r["text"]]
    confidences = [r["confidence"] for r in results if r["text"]]

    avg_conf = sum(confidences) / len(confidences) if confidences else 1.0

    if ocr_text:
        final_text = "\n\n".join(ocr_text)
        os.makedirs(os.path.dirname(text_path), exist_ok=True)
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(final_text)

        # Save metadata
        meta_path = os.path.join(base_dir, "text", "ocr_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "engine": "paddle",
                    "confidence": avg_conf,
                    "images_processed": len(images),
                },
                f,
            )

        return final_text, avg_conf

    return text, 0.0
