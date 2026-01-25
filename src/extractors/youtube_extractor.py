"""
YouTube Video Extractor 📺
==========================

Extracts content from YouTube videos by downloading audio and transcribing.
Follows the same interface as other extractors (PDF, Word, etc.).

Returns:
    - base_dir: Directory containing extracted content  
    - images: Empty list (videos don't have images to extract)
    - doc_id: Unique document identifier
    - source_type: "youtube"
"""
import os
import uuid
import json
import logging
import hashlib
from typing import Tuple, List

from services.media_service import download_youtube_audio, transcribe_audio, TranscriptionResult

logger = logging.getLogger(__name__)


def extract_youtube(youtube_url: str, output_base: str = None) -> Tuple[str, List[str], str, str]:
    """
    Extract content from a YouTube video.
    
    Args:
        youtube_url: The YouTube video URL
        output_base: Base directory for output (uses temp if None)
        
    Returns:
        Tuple of (base_dir, images, doc_id, source_type)
        
    Raises:
        ValueError: If URL is invalid or video unavailable
        RuntimeError: If extraction fails
    """
    import tempfile
    
    # Generate unique document ID
    url_hash = hashlib.md5(youtube_url.encode()).hexdigest()[:12]
    doc_id = f"{uuid.uuid4().hex[:8]}_{url_hash}"
    
    # Create output directory
    if output_base is None:
        output_base = tempfile.mkdtemp(prefix="documind_yt_")
    
    base_dir = os.path.join(output_base, doc_id)
    os.makedirs(base_dir, exist_ok=True)
    
    text_dir = os.path.join(base_dir, "text")
    os.makedirs(text_dir, exist_ok=True)
    
    audio_dir = os.path.join(base_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    
    logger.info(f"📺 Extracting YouTube: {youtube_url}")
    
    # Download audio
    audio_path = download_youtube_audio(youtube_url, audio_dir)
    
    # Transcribe
    transcription: TranscriptionResult = transcribe_audio(audio_path)
    
    # Build content text
    content_parts = []
    
    content_parts.append(f"# YouTube Video Transcript\n")
    content_parts.append(f"**Source:** {youtube_url}")
    content_parts.append(f"**Language:** {transcription.language}")
    content_parts.append(f"**Duration:** {transcription.duration:.1f} seconds\n")
    content_parts.append("---\n")
    content_parts.append("## Transcript\n")
    content_parts.append(transcription.text)
    
    # Add timestamped segments for reference
    if transcription.segments:
        content_parts.append("\n\n---\n\n## Timestamped Segments\n")
        for seg in transcription.segments:
            start_min = int(seg['start'] // 60)
            start_sec = int(seg['start'] % 60)
            content_parts.append(f"[{start_min:02d}:{start_sec:02d}] {seg['text']}")
    
    # Write content.txt
    content_text = "\n".join(content_parts)
    content_path = os.path.join(text_dir, "content.txt")
    with open(content_path, "w", encoding="utf-8") as f:
        f.write(content_text)
    
    # Write metadata.json
    metadata_path = os.path.join(base_dir, "metadata.json")
    metadata = {
        "youtube_url": youtube_url,
        "language": transcription.language,
        "duration_seconds": transcription.duration,
        "transcript_length": len(transcription.text),
        "segment_count": len(transcription.segments),
        "audio_file": os.path.basename(audio_path)
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Write segments.json for potential future use
    segments_path = os.path.join(base_dir, "segments.json")
    with open(segments_path, "w", encoding="utf-8") as f:
        json.dump(transcription.segments, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ YouTube extracted: {transcription.duration:.1f}s | {len(transcription.text)} chars")
    
    # Return empty images list (no images from YouTube transcription)
    return base_dir, [], doc_id, "youtube"


# Support for BaseExtractor interface (optional class-based usage)
class YouTubeExtractor:
    """
    YouTube video extractor class.
    Implements the BaseExtractor interface pattern.
    """
    
    @property
    def supported_extensions(self) -> List[str]:
        """YouTube extractor doesn't use file extensions."""
        return []
    
    def extract(self, youtube_url: str) -> Tuple[str, List[str], str, str]:
        """Extract content from YouTube URL."""
        return extract_youtube(youtube_url)
    
    def can_extract(self, url: str) -> bool:
        """Check if this is a valid YouTube URL."""
        from services.web_scraper_service import is_youtube_url
        return is_youtube_url(url)
