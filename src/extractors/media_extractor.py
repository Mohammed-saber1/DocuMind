"""
Media File Extractor 🎬
=======================

Extracts content from audio and video files by transcribing.
Follows the same interface as other extractors (PDF, Word, etc.).

Supported formats:
- Video: .mp4, .mkv, .avi, .mov, .webm, .flv, .wmv
- Audio: .mp3, .wav, .m4a, .ogg, .flac, .aac, .wma

Returns:
    - base_dir: Directory containing extracted content
    - images: Empty list (no images from audio/video)
    - doc_id: Unique document identifier
    - source_type: "video" or "audio"
"""

import os
import uuid
import json
import logging
from typing import Tuple, List

from services.media_service import (
    convert_to_mp3,
    transcribe_audio,
    TranscriptionResult,
    is_video_file,
    is_audio_file,
    is_media_file,
    SUPPORTED_VIDEO_EXTENSIONS,
    SUPPORTED_AUDIO_EXTENSIONS,
)

logger = logging.getLogger(__name__)


def extract_media(
    file_path: str, output_base: str = None
) -> Tuple[str, List[str], str, str]:
    """
    Extract content from an audio or video file.

    Args:
        file_path: Path to the audio/video file
        output_base: Base directory for output (uses temp if None)

    Returns:
        Tuple of (base_dir, images, doc_id, source_type)

    Raises:
        ValueError: If file is not a supported media format
        RuntimeError: If extraction fails
    """
    import tempfile

    if not os.path.exists(file_path):
        raise ValueError(f"File not found: {file_path}")

    if not is_media_file(file_path):
        ext = os.path.splitext(file_path)[1]
        raise ValueError(f"Unsupported media format: {ext}")

    # Determine source type
    source_type = "video" if is_video_file(file_path) else "audio"

    # Generate unique document ID
    filename = os.path.basename(file_path)
    doc_id = f"{uuid.uuid4().hex[:8]}_{os.path.splitext(filename)[0][:20]}"

    # Create output directory
    if output_base is None:
        output_base = tempfile.mkdtemp(prefix="documind_media_")

    base_dir = os.path.join(output_base, doc_id)
    os.makedirs(base_dir, exist_ok=True)

    text_dir = os.path.join(base_dir, "text")
    os.makedirs(text_dir, exist_ok=True)

    audio_dir = os.path.join(base_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    logger.info(f"🎬 Extracting {source_type}: {filename}")

    # Convert to MP3 if needed
    mp3_path = convert_to_mp3(file_path, audio_dir)

    # Transcribe
    transcription: TranscriptionResult = transcribe_audio(mp3_path)

    # Build content text
    content_parts = []

    content_parts.append(f"# {source_type.title()} Transcript\n")
    content_parts.append(f"**File:** {filename}")
    content_parts.append(f"**Language:** {transcription.language}")
    content_parts.append(f"**Duration:** {transcription.duration:.1f} seconds\n")
    content_parts.append("---\n")
    content_parts.append("## Transcript\n")
    content_parts.append(transcription.text)

    # Add timestamped segments for reference
    if transcription.segments:
        content_parts.append("\n\n---\n\n## Timestamped Segments\n")
        for seg in transcription.segments:
            start_min = int(seg["start"] // 60)
            start_sec = int(seg["start"] % 60)
            content_parts.append(f"[{start_min:02d}:{start_sec:02d}] {seg['text']}")

    # Save CSV transcription
    try:
        from services.media_service import save_transcription_to_csv

        # Save to base_dir so it's included in artifacts
        csv_path = save_transcription_to_csv(transcription, base_dir, filename)
    except Exception as e:
        logger.error(f"⚠️ Failed to save CSV transcription: {e}")

    # Write content.txt
    content_text = "\n".join(content_parts)
    content_path = os.path.join(text_dir, "content.txt")
    with open(content_path, "w", encoding="utf-8") as f:
        f.write(content_text)

    # Write metadata.json
    metadata_path = os.path.join(base_dir, "metadata.json")
    metadata = {
        "original_file": filename,
        "source_type": source_type,
        "language": transcription.language,
        "duration_seconds": transcription.duration,
        "transcript_length": len(transcription.text),
        "segment_count": len(transcription.segments),
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Write segments.json for potential future use
    segments_path = os.path.join(base_dir, "segments.json")
    with open(segments_path, "w", encoding="utf-8") as f:
        json.dump(transcription.segments, f, indent=2, ensure_ascii=False)

    logger.info(
        f"✅ Media extracted: {transcription.duration:.1f}s | {len(transcription.text)} chars"
    )

    # Return empty images list (no images from audio/video)
    return base_dir, [], doc_id, source_type


# Support for BaseExtractor interface (optional class-based usage)
class MediaExtractor:
    """
    Media file extractor class.
    Implements the BaseExtractor interface pattern.
    """

    @property
    def supported_extensions(self) -> List[str]:
        """List of supported media file extensions."""
        return SUPPORTED_VIDEO_EXTENSIONS + SUPPORTED_AUDIO_EXTENSIONS

    def extract(self, file_path: str) -> Tuple[str, List[str], str, str]:
        """Extract content from media file."""
        return extract_media(file_path)

    def can_extract(self, file_path: str) -> bool:
        """Check if file is a supported media format."""
        return is_media_file(file_path)
