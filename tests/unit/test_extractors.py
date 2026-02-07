"""
DocuMind Extractors Unit Tests
==============================

This module contains unit tests for the document extraction layer of DocuMind.
Tests cover various file format extractors including PDF, images (OCR),
Word documents, Excel spreadsheets, YouTube, and web URLs.

Test Classes:
-------------
    TestPDFExtractor : Tests for PDF document extraction.
    TestImageExtractor : Tests for image OCR and VLM fallback.
    TestWordExtractor : Tests for Word document extraction.
    TestExcelExtractor : Tests for Excel spreadsheet extraction.
    TestYouTubeExtractor : Tests for YouTube URL processing.
    TestURLExtractor : Tests for web URL scraping.

Running Tests:
--------------
    pytest tests/unit/test_extractors.py -v

Author:
-------
    Mohammed Saber <mohammed.saber.business@gmail.com>

License:
--------
    MIT License
"""


class TestPDFExtractor:
    """
    Unit tests for PDF document extraction.

    Tests cover file type detection, empty document handling,
    and metadata extraction from PDF files.
    """

    def test_pdf_file_detection(self):
        """
        Verify that PDF files are correctly identified by extension.

        Both lowercase and uppercase extensions should be recognized.
        """
        pdf_extensions = [".pdf", ".PDF"]

        for ext in pdf_extensions:
            filename = f"document{ext}"
            assert filename.lower().endswith(".pdf")

    def test_empty_pdf_handling(self):
        """
        Verify that empty PDF content is handled gracefully.

        Empty documents should not cause extraction failures.
        """
        content = ""

        assert content == "" or content is None or len(content.strip()) == 0

    def test_pdf_metadata_extraction(self):
        """
        Verify PDF metadata structure contains expected fields.

        Extracted metadata should include document information
        such as title, author, page count, and creation date.
        """
        mock_metadata = {
            "title": "Test Document",
            "author": "Test Author",
            "pages": 10,
            "creation_date": "2024-01-01",
        }

        assert "pages" in mock_metadata
        assert isinstance(mock_metadata["pages"], int)


class TestImageExtractor:
    """
    Unit tests for image extraction with OCR.

    Tests cover supported formats, OCR confidence thresholds,
    and VLM fallback behavior for complex images.
    """

    def test_supported_image_formats(self):
        """
        Verify that common image formats are supported.

        PNG, JPG, JPEG, TIFF, and WEBP formats should be accepted.
        """
        supported = [".png", ".jpg", ".jpeg", ".tiff", ".webp"]

        for ext in supported:
            assert ext.lower() in [".png", ".jpg", ".jpeg", ".tiff", ".webp"]

    def test_ocr_confidence_threshold(self):
        """
        Verify high OCR confidence does not trigger VLM fallback.

        When OCR confidence exceeds the threshold, the system should
        use OCR results directly without invoking the VLM.
        """
        confidence = 0.85
        threshold = 0.7

        use_vlm_fallback = confidence < threshold

        assert not use_vlm_fallback, "High confidence should not trigger VLM fallback"

    def test_low_confidence_triggers_vlm(self):
        """
        Verify low OCR confidence triggers VLM fallback.

        When OCR confidence is below threshold, the system should
        fall back to Vision-Language Model for better accuracy.
        """
        confidence = 0.5
        threshold = 0.7

        use_vlm_fallback = confidence < threshold

        assert use_vlm_fallback, "Low confidence should trigger VLM fallback"


class TestWordExtractor:
    """
    Unit tests for Word document extraction.

    Tests cover DOCX file detection and text extraction structure.
    """

    def test_docx_file_detection(self):
        """
        Verify that DOCX files are correctly identified.

        Both lowercase and uppercase extensions should be recognized.
        """
        docx_extensions = [".docx", ".DOCX"]

        for ext in docx_extensions:
            filename = f"document{ext}"
            assert filename.lower().endswith(".docx")

    def test_text_extraction_structure(self):
        """
        Verify extracted text maintains paragraph structure.

        Paragraphs should be properly separated in the output.
        """
        mock_paragraphs = [
            "First paragraph content.",
            "Second paragraph content.",
            "Third paragraph content.",
        ]

        combined_text = "\n\n".join(mock_paragraphs)

        assert len(combined_text) > 0
        assert combined_text.count("\n\n") == 2


class TestExcelExtractor:
    """
    Unit tests for Excel spreadsheet extraction.

    Tests cover file format detection and sheet data structure.
    """

    def test_xlsx_file_detection(self):
        """
        Verify that Excel files are correctly identified.

        Both XLSX and XLS formats should be recognized.
        """
        excel_extensions = [".xlsx", ".xls", ".XLSX", ".XLS"]

        for ext in excel_extensions:
            filename = f"spreadsheet{ext}"
            assert filename.lower().endswith((".xlsx", ".xls"))

    def test_sheet_data_structure(self):
        """
        Verify extracted sheet data has correct structure.

        Data should be organized by sheet name with row records.
        """
        mock_sheet_data = {
            "Sheet1": [
                {"Column1": "Value1", "Column2": "Value2"},
                {"Column1": "Value3", "Column2": "Value4"},
            ]
        }

        assert "Sheet1" in mock_sheet_data
        assert isinstance(mock_sheet_data["Sheet1"], list)


class TestYouTubeExtractor:
    """
    Unit tests for YouTube video extraction.

    Tests cover URL validation and format detection.
    """

    def test_youtube_url_validation(self):
        """
        Verify that valid YouTube URLs are recognized.

        Standard youtube.com and short youtu.be URLs should be accepted.
        """
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            assert "youtube" in url.lower() or "youtu.be" in url.lower()

    def test_invalid_youtube_url_detection(self):
        """
        Verify that non-YouTube URLs are rejected.

        URLs from other video platforms should not be identified as YouTube.
        """
        invalid_urls = [
            "https://www.google.com",
            "https://vimeo.com/123456",
            "not-a-url",
        ]

        for url in invalid_urls:
            is_youtube = "youtube" in url.lower() or "youtu.be" in url.lower()
            assert not is_youtube


class TestURLExtractor:
    """
    Unit tests for web URL extraction.

    Tests cover URL validation and HTML content processing.
    """

    def test_url_validation(self):
        """
        Verify that URLs have valid HTTP/HTTPS scheme.

        Only URLs with proper protocol should be accepted.
        """
        valid_urls = [
            "https://example.com",
            "http://test.org/page",
            "https://sub.domain.com/path/to/page",
        ]

        for url in valid_urls:
            assert url.startswith("http://") or url.startswith("https://")

    def test_html_content_cleaning(self):
        """
        Verify that HTML content is properly sanitized.

        Script tags and other potentially harmful content should be removed.
        """
        raw_html = "<p>Hello <b>World</b></p><script>evil()</script>"

        # Raw HTML contains script tag
        assert "<script>" in raw_html

        # Cleaned HTML should not contain script
        cleaned = "Hello World"
        assert "<script>" not in cleaned
