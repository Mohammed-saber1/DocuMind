
"""
Image Helper Utilities
======================

Helper functions to extract images from various file formats (DOCX, PDF)
to support multimodal processing pipelines.
"""

import os
import zipfile
import fitz  # PyMuPDF
from typing import List

def extract_images_from_docx(file_path: str, output_dir: str) -> List[str]:
    """
    Extract images from a DOCX file directly.
    """
    images = []
    counter = 1
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(file_path, "r") as z:
            for f in z.namelist():
                if f.startswith("word/media/"):
                    try:
                        data = z.read(f)
                        ext = os.path.splitext(f)[1]
                        # Use consistent naming convention
                        img_filename = f"img_docx_{counter}{ext}"
                        path = os.path.join(output_dir, img_filename)
                        
                        with open(path, "wb") as out:
                            out.write(data)
                        
                        images.append(path)
                        counter += 1
                    except Exception as e:
                        print(f"⚠️ Failed to extract image component {f}: {e}")
    except Exception as e:
        print(f"⚠️ Failed to unzip DOCX for images: {e}")
        
    return images


def extract_images_from_pdf(file_path: str, output_dir: str) -> List[str]:
    """
    Extract images from a PDF file using PyMuPDF.
    """
    images = []
    counter = 1
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    try:
        pdf_doc = fitz.open(file_path)
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = pdf_doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Filter small images
                    if len(image_bytes) < 10240: # < 10KB
                        continue
                        
                    img_filename = f"img_pdf_p{page_num+1}_{counter}.{image_ext}"
                    path = os.path.join(output_dir, img_filename)
                    
                    with open(path, "wb") as f:
                        f.write(image_bytes)
                        
                    images.append(path)
                    counter += 1
                except Exception as e:
                    print(f"⚠️ Failed to extract image {counter} from page {page_num}: {e}")
                    
        pdf_doc.close()
    except Exception as e:
        print(f"⚠️ Failed to process PDF for images: {e}")
        
    return images
