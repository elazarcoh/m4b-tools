"""
Shared utilities for M4B Tools.

This module contains common functions used across the converter and combiner modules.
"""

import os
import subprocess
import json
import re
import logging
import sys
from typing import List, Optional

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

# TypedDict definitions
class AudioMetadata(TypedDict, total=False):
    """Type definition for audio metadata."""
    duration: float
    title: str
    artist: str
    album: str
    album_artist: str
    author: str
    composer: str
    narrator: str
    genre: str
    date: str
    year: str
    comment: str
    description: str
    codec: str
    bitrate: str
    sample_rate: str
    channels: int

# Set up logging
logger = logging.getLogger(__name__)


def format_time(seconds: float) -> str:
    """Format seconds into a human-readable time string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


def check_ffmpeg() -> bool:
    """Check if FFmpeg is available in the system."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("FFmpeg/FFprobe is not installed or not found in PATH")
        return False


def natural_sort_key(filename: str) -> List:
    """Natural sorting key for filenames with numbers."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', filename)]


def get_audio_metadata(file_path: str) -> AudioMetadata:
    """Get audio file metadata including duration and format info."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        
        # Extract relevant information
        format_info = metadata.get('format', {})
        audio_stream = next((s for s in metadata.get('streams', []) if s.get('codec_type') == 'audio'), {})
        
        tags = format_info.get('tags', {})
        metadata: AudioMetadata = {
            'duration': float(format_info.get('duration', 0)),
            'title': tags.get('title', ''),
            'artist': tags.get('artist', ''),
            'album': tags.get('album', ''),
            'album_artist': tags.get('album_artist', ''),
            'author': tags.get('author', '') or tags.get('album_artist', ''),
            'composer': tags.get('composer', ''),
            'narrator': tags.get('narrator', '') or tags.get('composer', ''),
            'genre': tags.get('genre', ''),
            'date': tags.get('date', ''),
            'year': tags.get('year', '') or tags.get('date', '')[:4] if tags.get('date') else '',
            'comment': tags.get('comment', ''),
            'description': tags.get('description', '') or tags.get('comment', ''),
            'codec': audio_stream.get('codec_name', ''),
            'bitrate': audio_stream.get('bit_rate', ''),
            'sample_rate': audio_stream.get('sample_rate', ''),
            'channels': audio_stream.get('channels', 2)
        }
        return metadata
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Could not get metadata for {file_path}: {e}")
        return {}


def get_audio_duration(file_path: str) -> Optional[float]:
    """Get the duration of an audio file in seconds."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 
            'format=duration', '-of', 'csv=p=0', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        logger.warning(f"Could not get duration for {file_path}")
        return None


def ensure_output_directory(file_path: str) -> None:
    """Ensure the output directory exists for the given file path."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)