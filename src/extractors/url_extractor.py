"""
URL Content Extractor 🌐
========================

Extracts content from web URLs and formats it for the document pipeline.
Follows the same interface as other extractors (PDF, Word, etc.).

Returns:
    - base_dir: Directory containing extracted content
    - images: List of downloaded image paths
    - doc_id: Unique document identifier
    - source_type: "url"
"""
import os
import uuid
import logging
import hashlib
from typing import Tuple, List

from services.web_scraper_service import scrape_url, ScrapedContent

logger = logging.getLogger(__name__)


def extract_url(url: str, output_base: str = None) -> Tuple[str, List[str], str, str]:
    """
    Extract content from a web URL.
    
    Args:
        url: The web page URL to extract content from
        output_base: Base directory for output (uses temp if None)
        
    Returns:
        Tuple of (base_dir, images, doc_id, source_type)
        
    Raises:
        ValueError: If URL is invalid
        RuntimeError: If extraction fails
    """
    import tempfile
    
    # Generate unique document ID
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    doc_id = f"{uuid.uuid4().hex[:8]}_{url_hash}"
    
    # Create output directory
    if output_base is None:
        output_base = tempfile.mkdtemp(prefix="documind_url_")
    
    base_dir = os.path.join(output_base, doc_id)
    os.makedirs(base_dir, exist_ok=True)
    
    text_dir = os.path.join(base_dir, "text")
    os.makedirs(text_dir, exist_ok=True)
    
    logger.info(f"🌐 Extracting URL: {url}")
    
    # Scrape the URL
    scraped: ScrapedContent = scrape_url(url, output_dir=base_dir, download_images=True)
    
    # Build content text
    content_parts = []
    
    # Add title
    if scraped.title:
        content_parts.append(f"# {scraped.title}\n")
    
    # Add description
    if scraped.description:
        content_parts.append(f"**Description:** {scraped.description}\n")
    
    # Add source info
    content_parts.append(f"**Source:** {scraped.url}\n")
    
    # Add main text
    if scraped.main_text:
        content_parts.append(f"\n---\n\n{scraped.main_text}")
    
    # Add image references
    if scraped.images:
        content_parts.append("\n\n---\n\n## Referenced Images\n")
        for idx, img in enumerate(scraped.images, 1):
            alt_text = img.alt_text or f"Image {idx}"
            content_parts.append(f"- [{alt_text}]({img.url})")
    
    # Write content.txt
    content_text = "\n".join(content_parts)
    content_path = os.path.join(text_dir, "content.txt")
    with open(content_path, "w", encoding="utf-8") as f:
        f.write(content_text)
    
    # Write metadata.json
    import json
    metadata_path = os.path.join(base_dir, "metadata.json")
    metadata = {
        "url": scraped.url,
        "title": scraped.title,
        "description": scraped.description,
        "text_length": len(scraped.main_text),
        "image_count": len(scraped.images),
        **scraped.metadata
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Collect image paths
    images = [img.local_path for img in scraped.images if img.local_path]
    
    logger.info(f"✅ URL extracted: {scraped.title[:50]}... | {len(content_text)} chars | {len(images)} images")
    
    return base_dir, images, doc_id, "url"


# Support for BaseExtractor interface (optional class-based usage)
class URLExtractor:
    """
    URL content extractor class.
    Implements the BaseExtractor interface pattern.
    """
    
    @property
    def supported_extensions(self) -> List[str]:
        """URL extractor doesn't use file extensions."""
        return []
    
    def extract(self, url: str) -> Tuple[str, List[str], str, str]:
        """Extract content from URL."""
        return extract_url(url)
    
    def can_extract(self, url: str) -> bool:
        """Check if this is a valid URL."""
        from urllib.parse import urlparse
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except Exception:
            return False
