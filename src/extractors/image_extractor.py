"""Image file extractor."""
import os
from PIL import Image

from utils.file_utils import create_document_folder, save_text, save_metadata
try:
    from image_vision_vlm import VisionAnalyzer
except ImportError:
    VisionAnalyzer = None
    print("⚠️ Warning: image_vision_vlm module not found. Image analysis will be limited.")


def extract_image(file_path):
    """Extract image file and save to document folder."""
    doc_id, base, text_dir, img_dir = create_document_folder(file_path)

    img = Image.open(file_path)
    ext = os.path.splitext(file_path)[1]
    img_path = os.path.join(img_dir, f"img_1{ext}")
    img.save(img_path)

    description = ""
    source_type = "image"
    
    # VLM Analysis is now handled in the main pipeline based on OCR confidence
    # (See pipeline/document_pipeline.py)

    save_text(text_dir, description)
    save_metadata(base, {
        "source": source_type,
        "vlm_enabled": False, # VisionAnalyzer is not None,
        "description_length": len(description)
    })

    return base, [img_path], doc_id, source_type
