"""
Media Service 🎬
================

Handles audio/video processing for the DocuMind extraction pipeline:
- YouTube audio download (via yt-dlp)
- Audio/video to MP3 conversion (via FFmpeg)
- Audio transcription (via Whisper Large-v2)

All transcribed content is returned in a format compatible with the document pipeline.
"""
import os
import uuid
import tempfile
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""
    text: str
    language: str
    duration: float
    segments: list  # List of {start, end, text} dicts


def get_whisper_model():
    """
    Lazy-load Whisper model to avoid memory usage when not needed.
    Uses singleton pattern to avoid reloading.
    """
    global _whisper_model
    if '_whisper_model' not in globals() or _whisper_model is None:
        try:
            import whisper
            from core.config import get_settings
            settings = get_settings()
            
            logger.info(f"🔊 Loading Whisper model: {settings.whisper.model_size}")
            _whisper_model = whisper.load_model(
                settings.whisper.model_size,
                device=settings.whisper.device
            )
            logger.info("✅ Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            raise RuntimeError(f"Whisper initialization failed: {e}")
    return _whisper_model


def download_youtube_audio(youtube_url: str, output_dir: str = None) -> str:
    """
    Download audio from a YouTube video.
    
    Args:
        youtube_url: The YouTube video URL
        output_dir: Directory to save the audio file (uses temp dir if None)
        
    Returns:
        Path to the downloaded MP3 file
        
    Raises:
        ValueError: If the URL is invalid or video is unavailable
        RuntimeError: If download fails
    """
    import yt_dlp
    
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="documind_yt_")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate unique filename
    file_id = uuid.uuid4().hex[:12]
    output_path = os.path.join(output_dir, f"youtube_{file_id}.mp3")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path.replace('.mp3', '.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        logger.info(f"📥 Downloading YouTube audio: {youtube_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First, extract info to check availability
            info = ydl.extract_info(youtube_url, download=False)
            if info is None:
                raise ValueError("Video not found or unavailable")
            
            video_title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            logger.info(f"📹 Video: {video_title} (Duration: {duration}s)")
            
            # Now download
            ydl.download([youtube_url])
        
        # Find the actual output file (yt-dlp may change extension)
        actual_path = output_path.replace('.mp3', '.mp3')
        if not os.path.exists(actual_path):
            # Try to find the file
            for f in os.listdir(output_dir):
                if f.startswith(f"youtube_{file_id}"):
                    actual_path = os.path.join(output_dir, f)
                    break
        
        if not os.path.exists(actual_path):
            raise RuntimeError("Downloaded file not found")
            
        logger.info(f"✅ YouTube audio downloaded: {actual_path}")
        return actual_path
        
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Private video" in error_msg:
            raise ValueError("Video is private and cannot be accessed")
        elif "Video unavailable" in error_msg:
            raise ValueError("Video is unavailable or has been removed")
        elif "age-restricted" in error_msg.lower():
            raise ValueError("Video is age-restricted and cannot be downloaded")
        else:
            raise RuntimeError(f"YouTube download failed: {error_msg}")
    except Exception as e:
        raise RuntimeError(f"YouTube download failed: {e}")


def convert_to_mp3(input_path: str, output_dir: str = None) -> str:
    """
    Convert audio/video file to MP3 format using FFmpeg.
    
    Args:
        input_path: Path to the input audio/video file
        output_dir: Directory to save the MP3 (uses same dir as input if None)
        
    Returns:
        Path to the converted MP3 file
        
    Raises:
        ValueError: If input file doesn't exist
        RuntimeError: If conversion fails
    """
    import ffmpeg
    
    if not os.path.exists(input_path):
        raise ValueError(f"Input file not found: {input_path}")
    
    if output_dir is None:
        output_dir = os.path.dirname(input_path)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.mp3")
    
    # Skip conversion if already MP3
    if input_path.lower().endswith('.mp3'):
        logger.info("📝 File is already MP3, skipping conversion")
        return input_path
    
    try:
        logger.info(f"🔄 Converting to MP3: {input_path}")
        (
            ffmpeg
            .input(input_path)
            .output(output_path, acodec='libmp3lame', ab='192k', ac=2, ar='44100')
            .overwrite_output()
            .run(quiet=True, capture_stderr=True)
        )
        logger.info(f"✅ Converted to MP3: {output_path}")
        return output_path
        
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        raise RuntimeError(f"FFmpeg conversion failed: {stderr}")
    except Exception as e:
        raise RuntimeError(f"Audio conversion failed: {e}")


def transcribe_audio(audio_path: str) -> TranscriptionResult:
    """
    Transcribe audio file using Whisper Large-v2.
    
    Args:
        audio_path: Path to the audio file (MP3 preferred)
        
    Returns:
        TranscriptionResult with text, language, duration, and segments
        
    Raises:
        ValueError: If audio file doesn't exist
        RuntimeError: If transcription fails
    """
    if not os.path.exists(audio_path):
        raise ValueError(f"Audio file not found: {audio_path}")
    
    try:
        logger.info(f"🎤 Transcribing audio: {audio_path}")
        model = get_whisper_model()
        
        # Transcribe with word-level timestamps
        result = model.transcribe(
            audio_path,
            language=None,  # Auto-detect
            task="transcribe",
            verbose=False
        )
        
        # Extract segments
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip()
            })
        
        # Calculate duration from segments
        duration = segments[-1]["end"] if segments else 0
        
        transcription = TranscriptionResult(
            text=result["text"].strip(),
            language=result.get("language", "unknown"),
            duration=duration,
            segments=segments
        )
        
        logger.info(f"✅ Transcription complete | Language: {transcription.language} | Duration: {duration:.1f}s")
        return transcription
        
    except Exception as e:
        raise RuntimeError(f"Whisper transcription failed: {e}")


def process_youtube_to_text(youtube_url: str, output_dir: str = None) -> tuple[str, TranscriptionResult]:
    """
    Full pipeline: Download YouTube video and transcribe to text.
    
    Args:
        youtube_url: The YouTube video URL
        output_dir: Directory for temp files
        
    Returns:
        Tuple of (audio_path, TranscriptionResult)
    """
    # Download audio
    audio_path = download_youtube_audio(youtube_url, output_dir)
    
    # Transcribe
    result = transcribe_audio(audio_path)
    
    return audio_path, result


def process_media_to_text(media_path: str, output_dir: str = None) -> tuple[str, TranscriptionResult]:
    """
    Full pipeline: Convert media file to MP3 and transcribe.
    
    Args:
        media_path: Path to the audio/video file
        output_dir: Directory for temp files
        
    Returns:
        Tuple of (mp3_path, TranscriptionResult)
    """
    # Convert to MP3
    mp3_path = convert_to_mp3(media_path, output_dir)
    
    # Transcribe
    result = transcribe_audio(mp3_path)
    
    return mp3_path, result


# Supported media extensions
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv']
SUPPORTED_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.wma']
SUPPORTED_MEDIA_EXTENSIONS = SUPPORTED_VIDEO_EXTENSIONS + SUPPORTED_AUDIO_EXTENSIONS


def is_media_file(file_path: str) -> bool:
    """Check if file is a supported media file."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SUPPORTED_MEDIA_EXTENSIONS


def is_video_file(file_path: str) -> bool:
    """Check if file is a video file."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SUPPORTED_VIDEO_EXTENSIONS


def is_audio_file(file_path: str) -> bool:
    """Check if file is an audio file."""
def save_transcription_to_csv(transcription: TranscriptionResult, output_dir: str, filename_prefix: str) -> str:
    """
    Save transcription result to a CSV file with timestamps.
    
    Args:
        transcription: The TranscriptionResult object
        output_dir: Directory to save the CSV
        filename_prefix: Prefix for the filename (usually original filename)
        
    Returns:
        Path to the saved CSV file
    """
    import csv
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Clean filename
    clean_name = os.path.splitext(filename_prefix)[0]
    csv_path = os.path.join(output_dir, f"Transcription_{clean_name}.csv")
    
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["start_time", "end_time", "text"])

            for segment in transcription.segments:
                writer.writerow([
                    f"{segment['start']:.2f}",
                    f"{segment['end']:.2f}",
                    segment['text'].strip()
                ])
                
        logger.info(f"✅ Transcription saved to CSV: {csv_path}")
        return csv_path
        
    except Exception as e:
        logger.error(f"❌ Failed to write CSV: {e}")
        return None
