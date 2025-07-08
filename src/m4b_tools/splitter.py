"""
M4B file splitter functionality.

This module provides functions for splitting M4B files by chapters into various
audio formats while preserving metadata and supporting flexible naming templates.
"""

import os
import re
import subprocess
import json
import logging
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .utils import (
    check_ffmpeg, get_audio_metadata, ensure_output_directory, 
    AudioMetadata, format_time
)

# Set up logging
logger = logging.getLogger(__name__)

# Supported output formats for splitting
SUPPORTED_SPLIT_FORMATS = {'.mp3', '.m4a', '.m4b', '.aac', '.ogg', '.flac'}

# Default naming template
DEFAULT_TEMPLATE = "{book_title}/{chapter_num:02d} - {chapter_title}.{ext}"


class ChapterInfo:
    """Information about a chapter in an M4B file."""
    
    def __init__(self, title: str, start: float, end: float, index: int):
        self.title = title
        self.start = start
        self.end = end
        self.index = index
        self.duration = end - start
    
    def __repr__(self):
        return f"Chapter({self.index}: {self.title}, {self.start:.2f}-{self.end:.2f}s)"


def extract_chapters_from_m4b(file_path: str) -> Tuple[List[ChapterInfo], AudioMetadata]:
    """
    Extract chapter information and metadata from an M4B file.
    
    Args:
        file_path: Path to the M4B file
        
    Returns:
        Tuple of (chapters list, file metadata)
    """
    try:
        # Get chapters
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_chapters', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        chapters = []
        for i, chapter in enumerate(data.get('chapters', [])):
            start_time = float(chapter.get('start_time', 0))
            end_time = float(chapter.get('end_time', 0))
            title = chapter.get('tags', {}).get('title', f"Chapter {i + 1}")
            
            chapters.append(ChapterInfo(
                title=title,
                start=start_time,
                end=end_time,
                index=i + 1
            ))
        
        # If no chapters found, treat the whole file as one chapter
        if not chapters:
            metadata = get_audio_metadata(file_path)
            duration = metadata.get('duration', 0)
            if duration > 0:
                chapters.append(ChapterInfo(
                    title=metadata.get('title', 'Chapter 1'),
                    start=0,
                    end=duration,
                    index=1
                ))
        
        # Get file metadata
        file_metadata = get_audio_metadata(file_path)
        
        return chapters, file_metadata
        
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, Exception) as e:
        logger.error(f"Failed to extract chapters from {file_path}: {e}")
        return [], {}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    # Replace invalid characters with underscores
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '_', filename)
    
    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing whitespace and dots
    filename = filename.strip(' .')
    
    # Ensure filename is not empty
    if not filename:
        filename = "untitled"
    
    # Limit length to avoid filesystem issues
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename


def format_chapter_filename(template: str, chapter: ChapterInfo, metadata: AudioMetadata, 
                          output_format: str, file_path: str) -> str:
    """
    Format a chapter filename using the given template.
    
    Args:
        template: Naming template string
        chapter: Chapter information
        metadata: File metadata
        output_format: Output format extension (without dot)
        file_path: Original file path
        
    Returns:
        Formatted filename path
    """
    # Prepare template variables
    author_raw = metadata.get('author', '') or metadata.get('artist', '') or metadata.get('album_artist', '')
    narrator_raw = metadata.get('narrator', '') or metadata.get('composer', '')
    genre_raw = metadata.get('genre', '')
    
    variables = {
        'chapter_num': chapter.index,
        'chapter_title': sanitize_filename(chapter.title),
        'book_title': sanitize_filename(metadata.get('title', '') or 
                                      metadata.get('album', '') or 
                                      Path(file_path).stem),
        'author': sanitize_filename(author_raw) if author_raw else '',
        'narrator': sanitize_filename(narrator_raw) if narrator_raw else '',
        'genre': sanitize_filename(genre_raw) if genre_raw else '',
        'year': metadata.get('year', ''),
        'ext': output_format,
        'original_filename': Path(file_path).stem,
        'duration': f"{chapter.duration:.0f}s",
        'duration_formatted': format_time(chapter.duration)
    }
    
    # Format the template
    try:
        formatted = template.format(**variables)
    except KeyError as e:
        logger.warning(f"Unknown template variable {e}, using default template")
        formatted = DEFAULT_TEMPLATE.format(**variables)
    
    return formatted


def split_chapter(file_path: str, chapter: ChapterInfo, output_path: str, 
                 output_format: str, metadata: AudioMetadata) -> bool:
    """
    Split a single chapter from an M4B file.
    
    Args:
        file_path: Path to the source M4B file
        chapter: Chapter information
        output_path: Output file path
        output_format: Output format extension
        metadata: Original file metadata
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure output directory exists
        ensure_output_directory(output_path)
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-i', file_path,
            '-ss', str(chapter.start),
            '-t', str(chapter.duration),
            '-vn',  # No video
            '-map_metadata', '0',  # Copy metadata
            '-y'  # Overwrite output
        ]
        
        # Add format-specific options
        if output_format == 'mp3':
            cmd.extend(['-acodec', 'libmp3lame', '-b:a', '128k'])
        elif output_format == 'm4a':
            cmd.extend(['-acodec', 'aac', '-b:a', '128k'])
        elif output_format == 'm4b':
            cmd.extend(['-acodec', 'aac', '-b:a', '64k'])
        elif output_format == 'flac':
            cmd.extend(['-acodec', 'flac'])
        elif output_format == 'ogg':
            cmd.extend(['-acodec', 'libvorbis', '-b:a', '128k'])
        elif output_format == 'aac':
            cmd.extend(['-acodec', 'aac', '-b:a', '128k'])
        
        # Add metadata tags
        if metadata.get('title'):
            cmd.extend(['-metadata', f'album={metadata.get("title")}'])
        if metadata.get('author'):
            cmd.extend(['-metadata', f'artist={metadata.get("author")}'])
            cmd.extend(['-metadata', f'album_artist={metadata.get("author")}'])
        if metadata.get('narrator'):
            cmd.extend(['-metadata', f'composer={metadata.get("narrator")}'])
        if metadata.get('genre'):
            cmd.extend(['-metadata', f'genre={metadata.get("genre")}'])
        if metadata.get('year'):
            cmd.extend(['-metadata', f'date={metadata.get("year")}'])
        
        # Set chapter-specific metadata
        cmd.extend(['-metadata', f'title={chapter.title}'])
        cmd.extend(['-metadata', f'track={chapter.index}'])
        
        cmd.append(output_path)
        
        logger.info(f"Extracting chapter {chapter.index}: {chapter.title}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Verify output file
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"✅ Chapter {chapter.index} extracted ({file_size_mb:.1f}MB)")
            return True
        else:
            logger.error(f"Output file not created or empty: {output_path}")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error extracting chapter {chapter.index}: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error extracting chapter {chapter.index}: {str(e)}")
        return False


def split_m4b_file(file_path: str, output_dir: str, output_format: str = 'mp3',
                  template: str = DEFAULT_TEMPLATE, max_workers: int = 1) -> Tuple[int, int]:
    """
    Split an M4B file into chapters.
    
    Args:
        file_path: Path to the M4B file to split
        output_dir: Base output directory
        output_format: Output format (mp3, m4a, m4b, etc.)
        template: Naming template for output files
        max_workers: Number of parallel workers for extraction
        
    Returns:
        Tuple of (successful_chapters, total_chapters)
    """
    if not check_ffmpeg():
        logger.error("FFmpeg is required for splitting M4B files")
        return 0, 0
    
    # Validate output format
    if f'.{output_format}' not in SUPPORTED_SPLIT_FORMATS:
        logger.error(f"Unsupported output format: {output_format}")
        logger.info(f"Supported formats: {', '.join(f[1:] for f in SUPPORTED_SPLIT_FORMATS)}")
        return 0, 0
    
    # Extract chapters and metadata
    chapters, metadata = extract_chapters_from_m4b(file_path)
    if not chapters:
        logger.error(f"No chapters found in {file_path}")
        return 0, 0
    
    logger.info(f"Found {len(chapters)} chapters in {os.path.basename(file_path)}")
    
    # Process chapters
    successful = 0
    tasks = []
    
    # Prepare all tasks
    for chapter in chapters:
        output_filename = format_chapter_filename(
            template, chapter, metadata, output_format, file_path
        )
        output_path = os.path.join(output_dir, output_filename)
        tasks.append((chapter, output_path))
    
    # Execute tasks
    if max_workers == 1:
        # Sequential processing
        for chapter, output_path in tasks:
            if split_chapter(file_path, chapter, output_path, output_format, metadata):
                successful += 1
    else:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chapter = {
                executor.submit(split_chapter, file_path, chapter, output_path, 
                              output_format, metadata): chapter
                for chapter, output_path in tasks
            }
            
            for future in as_completed(future_to_chapter):
                if future.result():
                    successful += 1
    
    return successful, len(chapters)


def split_multiple_m4b_files(pattern: str, output_dir: str, output_format: str = 'mp3',
                           template: str = DEFAULT_TEMPLATE, max_workers: int = 1) -> Tuple[int, int]:
    """
    Split multiple M4B files matching a pattern.
    
    Args:
        pattern: Glob pattern to match M4B files
        output_dir: Base output directory
        output_format: Output format for chapters
        template: Naming template for output files
        max_workers: Number of parallel workers
        
    Returns:
        Tuple of (successful_files, total_files)
    """
    import glob
    
    # Find matching files
    files = glob.glob(pattern, recursive=True)
    m4b_files = [f for f in files if f.lower().endswith('.m4b')]
    
    if not m4b_files:
        logger.error(f"No M4B files found matching pattern: {pattern}")
        return 0, 0
    
    logger.info(f"Found {len(m4b_files)} M4B files to split")
    
    successful_files = 0
    total_chapters = 0
    successful_chapters = 0
    
    for file_path in m4b_files:
        logger.info(f"Processing: {os.path.basename(file_path)}")
        succ, total = split_m4b_file(file_path, output_dir, output_format, template, max_workers)
        successful_chapters += succ
        total_chapters += total
        
        if succ == total and total > 0:
            successful_files += 1
        
        logger.info(f"Completed {os.path.basename(file_path)}: {succ}/{total} chapters")
    
    logger.info(f"Split complete: {successful_files}/{len(m4b_files)} files, "
               f"{successful_chapters}/{total_chapters} chapters")
    
    return successful_files, len(m4b_files)
