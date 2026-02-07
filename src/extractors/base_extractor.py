"""
Base extractor interface.

All document extractors should inherit from this abstract base class
to ensure consistent interface across different file types.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple


class BaseExtractor(ABC):
    """
    Abstract base class for document extractors.

    Provides a consistent interface for extracting content
    from different document types.
    """

    @abstractmethod
    def extract(self, file_path: str) -> Tuple[str, List[str], str, str]:
        """
        Extract content from a document.

        Args:
            file_path: Absolute path to the document file

        Returns:
            Tuple containing:
                - base_dir: Directory where extracted content is saved
                - images: List of paths to extracted images
                - doc_id: Unique document identifier
                - source_type: Type of source document (e.g., 'pdf', 'docx')
        """

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """
        List of supported file extensions.

        Returns:
            List of file extensions this extractor can handle (e.g., ['.pdf'])
        """

    def can_extract(self, file_path: str) -> bool:
        """
        Check if this extractor can handle the given file.

        Args:
            file_path: Path to the file to check

        Returns:
            True if this extractor supports the file type
        """
        import os

        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_extensions
