"""File type enumeration."""
from enum import Enum


class FileTypeEnum(str, Enum):
    """Supported file types for document extraction."""
    
    # Documents
    PDF = "pdf"
    WORD = "docx"
    POWERPOINT = "pptx"
    
    # Spreadsheets
    EXCEL_XLSX = "xlsx"
    EXCEL_XLS = "xls"
    EXCEL_XLSM = "xlsm"
    CSV = "csv"
    
    # Images
    IMAGE_PNG = "png"
    IMAGE_JPG = "jpg"
    IMAGE_JPEG = "jpeg"
    IMAGE_BMP = "bmp"
    IMAGE_TIFF = "tiff"
    IMAGE_WEBP = "webp"
    
    @classmethod
    def get_document_types(cls) -> list:
        """Get list of document file types."""
        return [cls.PDF, cls.WORD, cls.POWERPOINT]
    
    @classmethod
    def get_spreadsheet_types(cls) -> list:
        """Get list of spreadsheet file types."""
        return [cls.EXCEL_XLSX, cls.EXCEL_XLS, cls.EXCEL_XLSM, cls.CSV]
    
    @classmethod
    def get_image_types(cls) -> list:
        """Get list of image file types."""
        return [
            cls.IMAGE_PNG, cls.IMAGE_JPG, cls.IMAGE_JPEG,
            cls.IMAGE_BMP, cls.IMAGE_TIFF, cls.IMAGE_WEBP
        ]
