"""
Web Scraper Service 🌐
======================

Handles web page content extraction for the DocuMind extraction pipeline:
- Fetches web pages with proper headers
- Extracts main text content
- Downloads referenced images
- Extracts metadata (title, description, etc.)

Returns content in a format compatible with the document pipeline.
"""

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapedImage:
    """Represents a scraped image."""

    url: str
    local_path: Optional[str] = None
    alt_text: str = ""


@dataclass
class ScrapedContent:
    """Result of web page scraping."""

    url: str
    title: str
    description: str
    main_text: str
    images: List[ScrapedImage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def _get_headers() -> dict:
    """Get HTTP headers for requests."""
    settings = get_settings()
    return {
        "User-Agent": settings.scraper.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def _validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except Exception:
        return False


def _extract_main_text(soup: BeautifulSoup) -> str:
    """
    Extract main text content from HTML.
    Removes scripts, styles, nav, footer, etc.
    """
    # Remove unwanted elements
    for element in soup.find_all(
        [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form",
            "noscript",
            "iframe",
        ]
    ):
        element.decompose()

    # Try to find main content area
    main_content = None

    # Common main content selectors
    selectors = [
        "article",
        "main",
        '[role="main"]',
        ".main-content",
        "#main-content",
        ".post-content",
        ".entry-content",
        ".article-body",
        "#content",
        ".content",
    ]

    for selector in selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break

    # Fall back to body if no main content found
    if not main_content:
        main_content = soup.find("body")

    if not main_content:
        return ""

    # Get text with proper spacing
    text_parts = []
    for element in main_content.stripped_strings:
        text_parts.append(element)

    # Join with newlines, clean up excessive whitespace
    text = "\n".join(text_parts)
    text = re.sub(r"\n{3,}", "\n\n", text)  # Max 2 consecutive newlines
    text = re.sub(r" {2,}", " ", text)  # Max 1 consecutive space

    return text.strip()


def _extract_metadata(soup: BeautifulSoup, url: str) -> dict:
    """Extract page metadata."""
    metadata = {
        "url": url,
        "domain": urlparse(url).netloc,
    }

    # Open Graph metadata
    og_tags = ["og:title", "og:description", "og:image", "og:type", "og:site_name"]
    for tag in og_tags:
        meta = soup.find("meta", property=tag)
        if meta and meta.get("content"):
            key = tag.replace("og:", "og_")
            metadata[key] = meta["content"]

    # Twitter metadata
    twitter_tags = ["twitter:title", "twitter:description", "twitter:image"]
    for tag in twitter_tags:
        meta = soup.find("meta", attrs={"name": tag})
        if meta and meta.get("content"):
            key = tag.replace("twitter:", "twitter_")
            metadata[key] = meta["content"]

    # Standard metadata
    keywords = soup.find("meta", attrs={"name": "keywords"})
    if keywords and keywords.get("content"):
        metadata["keywords"] = keywords["content"]

    author = soup.find("meta", attrs={"name": "author"})
    if author and author.get("content"):
        metadata["author"] = author["content"]

    # Canonical URL
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        metadata["canonical_url"] = canonical["href"]

    return metadata


def _download_image(img_url: str, output_dir: str, base_url: str) -> Optional[str]:
    """Download an image and return local path."""
    try:
        # Resolve relative URLs
        if not img_url.startswith(("http://", "https://")):
            img_url = urljoin(base_url, img_url)

        # Skip data URLs and SVGs
        if img_url.startswith("data:") or img_url.endswith(".svg"):
            return None

        settings = get_settings()
        response = requests.get(
            img_url,
            headers=_get_headers(),
            timeout=settings.scraper.timeout,
            stream=True,
        )
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get("content-type", "")
        if "image" not in content_type:
            return None

        # Generate filename from URL hash
        url_hash = hashlib.md5(img_url.encode()).hexdigest()[:12]
        ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
        filename = f"scraped_{url_hash}{ext}"
        local_path = os.path.join(output_dir, filename)

        # Download image
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return local_path

    except Exception as e:
        logger.warning(f"⚠️ Failed to download image {img_url}: {e}")
        return None


def scrape_url(
    url: str, output_dir: str = None, download_images: bool = True
) -> ScrapedContent:
    """
    Scrape content from a web URL.

    Args:
        url: The web page URL to scrape
        output_dir: Directory to save downloaded images
        download_images: Whether to download referenced images

    Returns:
        ScrapedContent with extracted text, title, and images

    Raises:
        ValueError: If URL is invalid
        RuntimeError: If scraping fails
    """
    # Validate URL
    if not _validate_url(url):
        raise ValueError(f"Invalid URL format: {url}")

    settings = get_settings()

    try:
        logger.info(f"🌐 Scraping URL: {url}")

        # Fetch page
        response = requests.get(
            url,
            headers=_get_headers(),
            timeout=settings.scraper.timeout,
            allow_redirects=True,
        )
        response.raise_for_status()

        # Check content length
        content_length = len(response.content)
        if content_length > settings.scraper.max_content_length:
            raise ValueError(f"Page content too large: {content_length} bytes")

        # Parse HTML
        soup = BeautifulSoup(response.content, "lxml")

        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()

        # Extract description
        description = ""
        desc_meta = soup.find("meta", attrs={"name": "description"})
        if desc_meta and desc_meta.get("content"):
            description = desc_meta["content"]
        elif soup.find("meta", property="og:description"):
            description = soup.find("meta", property="og:description").get(
                "content", ""
            )

        # Extract main text
        main_text = _extract_main_text(soup)

        if not main_text:
            logger.warning("⚠️ No main text content found on page")

        # Extract metadata
        metadata = _extract_metadata(soup, url)

        # Extract and optionally download images
        images = []
        if download_images and output_dir:
            img_dir = os.path.join(output_dir, "images")
            os.makedirs(img_dir, exist_ok=True)

            for img in soup.find_all("img"):
                img_url = img.get("src") or img.get("data-src")
                if not img_url:
                    continue

                alt_text = img.get("alt", "")
                local_path = _download_image(img_url, img_dir, url)

                images.append(
                    ScrapedImage(url=img_url, local_path=local_path, alt_text=alt_text)
                )

            # Filter to only successfully downloaded images
            images = [img for img in images if img.local_path]
            logger.info(f"📷 Downloaded {len(images)} images")

        result = ScrapedContent(
            url=url,
            title=title,
            description=description,
            main_text=main_text,
            images=images,
            metadata=metadata,
        )

        logger.info(f"✅ Scraped: {title[:50]}... ({len(main_text)} chars)")
        return result

    except requests.exceptions.Timeout:
        raise RuntimeError(f"Request timed out for URL: {url}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Failed to connect to URL: {url}")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"HTTP error {e.response.status_code} for URL: {url}")
    except Exception as e:
        raise RuntimeError(f"Failed to scrape URL: {e}")


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube video URL."""
    if not url:
        return False
    patterns = [
        r"(youtube\.com/watch\?v=)",
        r"(youtu\.be/)",
        r"(youtube\.com/embed/)",
        r"(youtube\.com/v/)",
    ]
    return any(re.search(pattern, url) for pattern in patterns)


def normalize_youtube_url(url: str) -> str:
    """
    Normalize YouTube URL to standard format.

    Returns:
        Standard YouTube URL format: https://www.youtube.com/watch?v=VIDEO_ID
    """
    # Extract video ID
    patterns = [
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]+)",
        r"youtu\.be/([a-zA-Z0-9_-]+)",
        r"youtube\.com/embed/([a-zA-Z0-9_-]+)",
        r"youtube\.com/v/([a-zA-Z0-9_-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"

    return url
