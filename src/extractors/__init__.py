"""
Extractors module for document content extraction.

This module provides extractors for different document types:

- pdf_extractor: PDF files using PyMuPDF and pdfplumber
- word_extractor: DOCX files using python-docx
- excel_extractor: Excel and CSV files using openpyxl/xlrd
- ppt_extractor: PowerPoint files using python-pptx
- image_extractor: Image files for OCR/VLM processing
- url_extractor: Web page content via scraping
- youtube_extractor: YouTube video transcription
- media_extractor: Audio/video file transcription
- base_extractor: Abstract base class for all extractors
"""

from extractors.pdf_extractor import extract_pdf
from extractors.word_extractor import extract_word
from extractors.excel_extractor import extract_excel, extract_csv
from extractors.ppt_extractor import extract_ppt
from extractors.image_extractor import extract_image
from extractors.url_extractor import extract_url
from extractors.youtube_extractor import extract_youtube
from extractors.media_extractor import extract_media
from extractors.base_extractor import BaseExtractor

__all__ = [
    "extract_pdf",
    "extract_word",
    "extract_excel",
    "extract_csv",
    "extract_ppt",
    "extract_image",
    "extract_url",
    "extract_youtube",
    "extract_media",
    "BaseExtractor",
]
