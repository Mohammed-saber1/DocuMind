"""PDF file extractor using hybrid approach: PyMuPDF for text/images, pdfplumber for tables."""

import os
import uuid
import fitz  # PyMuPDF
import pdfplumber

from utils.file_utils import (
    create_document_folder,
    save_text,
    save_metadata,
    save_tables,
)
from utils.table_utils import format_table_as_markdown


def extract_pdf(file_path):
    """
    Extract text, tables, and images from PDF file.
    Uses PyMuPDF (fitz) for text/images (faster, better quality)
    Uses pdfplumber for tables (more accurate detection)
    """
    doc_id, base, text_dir, img_dir = create_document_folder(file_path)

    text = ""
    images = []
    tables_data = []
    counter = 1

    # Open with PyMuPDF for text and images
    pdf_doc = fitz.open(file_path)

    # Open with pdfplumber for tables
    plumber_pdf = pdfplumber.open(file_path)

    try:
        for page_num in range(len(pdf_doc)):
            pymupdf_page = pdf_doc[page_num]
            plumber_page = plumber_pdf.pages[page_num]

            # --- TABLES (using pdfplumber - better detection) ---
            page_tables = plumber_page.extract_tables()
            if page_tables:
                for table_idx, table in enumerate(page_tables, 1):
                    if table:
                        tables_data.append(
                            {
                                "page": page_num + 1,
                                "table_index": table_idx,
                                "data": table,
                            }
                        )
                        text += f"\n\n[TABLE {page_num + 1}-{table_idx}]\n"
                        text += format_table_as_markdown(table)
                        text += "\n"

            # --- TEXT (using PyMuPDF - faster, preserves layout) ---
            page_text = pymupdf_page.get_text("text")
            if page_text:
                text += page_text + "\n"

            # --- IMAGES (using PyMuPDF - better quality, includes vector graphics) ---
            image_list = pymupdf_page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]  # Image reference number
                    base_image = pdf_doc.extract_image(xref)

                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # --- FILTER: Skip small images/icons ---
                    # Check size (bytes)
                    if len(image_bytes) < 10240:  # < 10KB
                        continue

                    # Check dimensions (width/height) via pixmap
                    try:
                        pix = fitz.Pixmap(pdf_doc, xref)
                        if pix.width < 100 or pix.height < 100:  # Skip small dimensions
                            pix = None
                            continue
                        pix = None
                    except Exception:
                        pass
                    # ----------------------------------------

                    # Save image
                    img_path = os.path.join(img_dir, f"img_{counter}.{image_ext}")
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)

                    images.append(img_path)
                    counter += 1

                except Exception as e:
                    print(
                        f"⚠️ Failed to extract image {counter} from page {page_num + 1}: {e}"
                    )
                    continue

    finally:
        pdf_doc.close()
        plumber_pdf.close()

    # Save tables separately as JSON
    if tables_data:
        save_tables(base, tables_data)
        print(f"📊 Found {len(tables_data)} table(s) in PDF")

    save_text(text_dir, text)
    save_metadata(
        base,
        {
            "source": "pdf",
            "extraction_method": "hybrid (PyMuPDF + pdfplumber)",
            "images_found": len(images),
            "tables_found": len(tables_data),
        },
    )

    print(f"✅ Extracted {len(images)} image(s) using PyMuPDF")
    return base, images, doc_id, "pdf"
