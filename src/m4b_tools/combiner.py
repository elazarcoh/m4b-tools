"""
M4B file combiner functionality.

This module provides functions for combining multiple M4B files into a single file
with chapters, generating CSV templates, and managing metadata.
"""

import os
import glob
import subprocess
import tempfile
import json
import re
import csv
import urllib.request
import urllib.parse
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
from contextlib import nullcontext

from .utils import (
    check_ffmpeg, format_time, natural_sort_key, 
    get_audio_metadata, ensure_output_directory
)

# Set up logging
logger = logging.getLogger(__name__)


def extract_existing_chapters(file_path: str) -> List[Dict]:
    """Extract existing chapter information from an M4B file."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_chapters', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        chapters = []
        for chapter in data.get('chapters', []):
            start_time = float(chapter.get('start_time', 0))
            end_time = float(chapter.get('end_time', 0))
            title = chapter.get('tags', {}).get('title', f"Chapter {len(chapters) + 1}")
            
            chapters.append({
                'title': title,
                'start': start_time,
                'end': end_time,
                'duration': end_time - start_time
            })
        
        return chapters
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.warning(f"Could not extract chapters from {file_path}: {e}")
        return []


def create_concat_file(files: List[str], temp_dir: str) -> str:
    """Create a temporary concat file for FFmpeg."""
    concat_path = os.path.join(temp_dir, 'concat_list.txt')
    with open(concat_path, 'w', encoding='utf-8') as f:
        for file_path in files:
            # Escape special characters for FFmpeg concat format
            # Replace single quotes with escaped single quotes and wrap in single quotes
            escaped_path = file_path.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    return concat_path


def create_chapter_metadata(chapters: List[Dict], temp_dir: str, metadata: Dict) -> str:
    """Create FFmpeg metadata file with chapter information."""
    metadata_path = os.path.join(temp_dir, 'metadata.txt')
    
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(";FFMETADATA1\n")
        
        # Add book metadata
        if metadata.get('title'):
            f.write(f"title={metadata['title']}\n")
        if metadata.get('artist'):
            f.write(f"artist={metadata['artist']}\n")
        if metadata.get('album'):
            f.write(f"album={metadata['album']}\n")
        if metadata.get('author'):
            f.write(f"album_artist={metadata['author']}\n")
        if metadata.get('narrator'):
            f.write(f"composer={metadata['narrator']}\n")
        if metadata.get('genre'):
            f.write(f"genre={metadata['genre']}\n")
        if metadata.get('year'):
            f.write(f"date={metadata['year']}\n")
        if metadata.get('description'):
            f.write(f"comment={metadata['description']}\n")
        
        f.write("\n")
        
        # Add chapters
        for chapter in chapters:
            f.write("[CHAPTER]\n")
            f.write("TIMEBASE=1/1000\n")
            f.write(f"START={int(chapter['start'] * 1000)}\n")
            f.write(f"END={int(chapter['end'] * 1000)}\n")
            f.write(f"title={chapter['title']}\n")
            f.write("\n")
    
    return metadata_path


def check_audio_compatibility(files_metadata: List[Dict]) -> bool:
    """Check if all files have compatible audio parameters."""
    if not files_metadata:
        return False
    
    first_file = files_metadata[0]
    reference_codec = first_file.get('codec')
    reference_sample_rate = first_file.get('sample_rate')
    reference_channels = first_file.get('channels')
    
    for metadata in files_metadata[1:]:
        if (metadata.get('codec') != reference_codec or
            metadata.get('sample_rate') != reference_sample_rate or
            metadata.get('channels') != reference_channels):
            return False
    
    return True


def download_cover_art(url: str, temp_dir: str) -> Optional[str]:
    """
    Download cover art from URL to temporary directory.
    
    Args:
        url: URL to download cover art from
        temp_dir: Temporary directory to save the image
        
    Returns:
        Path to downloaded file, or None if download failed
    """
    try:
        # Parse URL to get file extension
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        
        # Try to determine file extension from URL
        ext = os.path.splitext(path)[1].lower()
        if not ext or ext not in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}:
            # Default to .jpg if no extension or unknown extension
            ext = '.jpg'
        
        output_path = os.path.join(temp_dir, f'cover{ext}')
        
        logger.info(f"Downloading cover art from: {url}")
        with urllib.request.urlopen(url) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())
        
        # Verify the file was downloaded and has content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Cover art downloaded: {output_path}")
            return output_path
        else:
            logger.warning("Downloaded cover art file is empty")
            return None
            
    except Exception as e:
        logger.warning(f"Failed to download cover art from {url}: {e}")
        return None


def derive_chapter_title(file_path: str, index: int, existing_title: str = "") -> str:
    """
    Derive a chapter title from file path, index, and existing title.
    
    Args:
        file_path: Path to the audio file
        index: Chapter index (1-based)
        existing_title: Existing title from metadata
        
    Returns:
        Derived chapter title
    """
    if existing_title.strip():
        return existing_title.strip()
    
    # Extract filename without extension
    filename = Path(file_path).stem
    
    # Try to extract meaningful title from filename
    # Remove common prefixes like "Chapter", "Ch", "Part", "Pt"
    cleaned = re.sub(r'^(chapter|ch|part|pt)[\s\-_]*\d*[\s\-_]*', '', filename, flags=re.IGNORECASE)
    
    # Remove leading numbers
    cleaned = re.sub(r'^\d+[\s\-_]*', '', cleaned)
    
    # Replace underscores and hyphens with spaces
    cleaned = cleaned.replace('_', ' ').replace('-', ' ')
    
    # Normalize whitespace
    cleaned = ' '.join(cleaned.split())
    
    if cleaned:
        return cleaned.title()
    else:
        return f"Chapter {index}"


def generate_csv_from_folder(folder_path: str, output_csv: str = None) -> bool:
    """
    Generate a CSV template file from a folder containing M4B files.
    
    Args:
        folder_path: Path to folder containing M4B files
        output_csv: Output CSV file path (defaults to folder_name.csv)
        
    Returns:
        True if successful, False otherwise
    """
    folder_path = os.path.abspath(folder_path)
    
    if not os.path.exists(folder_path):
        logger.error(f"Folder not found: {folder_path}")
        return False
    
    if not os.path.isdir(folder_path):
        logger.error(f"Path is not a directory: {folder_path}")
        return False
    
    # Find all M4B files in the folder
    m4b_files = []
    for file_path in glob.glob(os.path.join(folder_path, "**", "*"), recursive=True):
        if os.path.isfile(file_path) and Path(file_path).suffix.lower() in {'.m4b', '.m4a'}:
            m4b_files.append(file_path)
    
    if not m4b_files:
        logger.error(f"No M4B files found in folder: {folder_path}")
        return False
    
    # Sort files naturally
    m4b_files.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
    
    # Generate output CSV path if not provided
    if not output_csv:
        folder_name = os.path.basename(folder_path)
        output_csv = os.path.join(folder_path, f"{folder_name}.csv")
    else:
        output_csv = os.path.abspath(output_csv)
    
    # Generate folder-based metadata
    folder_name = os.path.basename(folder_path)
    output_m4b = os.path.join(folder_path, f"{folder_name}.m4b")
    
    logger.info(f"Generating CSV template for {len(m4b_files)} M4B files...")
    
    try:
        with open(output_csv, 'w', encoding='utf-8', newline='') as f:
            # Write metadata headers
            f.write(f"#title,{folder_name}\n")
            f.write("#author,\n")
            f.write("#narrator,\n")
            f.write("#genre,Audiobook\n")
            f.write("#year,\n")
            f.write("#description,\n")
            f.write(f"#output_path,{output_m4b}\n")
            f.write("#cover_path,\n")
            f.write("\n")
            
            # Write CSV header
            writer = csv.writer(f)
            writer.writerow(['file', 'title'])
            
            # Write file entries
            for file_path in m4b_files:
                # Make path relative to CSV file directory
                rel_path = os.path.relpath(file_path, os.path.dirname(output_csv))
                
                # First try to get title from file metadata
                metadata = get_audio_metadata(file_path)
                metadata_title = metadata.get('title', '').strip() if metadata else ''
                
                if metadata_title:
                    # Use metadata title if available
                    chapter_title = metadata_title
                else:
                    # Fall back to generating chapter title from filename
                    filename = Path(file_path).stem
                    # Clean up filename for chapter title
                    cleaned = re.sub(r'^(chapter|ch|part|pt)[\s\-_]*\d*[\s\-_]*', '', filename, flags=re.IGNORECASE)
                    cleaned = re.sub(r'^\d+[\s\-_]*', '', cleaned)  # Remove leading numbers
                    cleaned = cleaned.replace('_', ' ').replace('-', ' ')
                    cleaned = ' '.join(cleaned.split())  # Normalize whitespace
                    
                    if cleaned:
                        chapter_title = cleaned.title()
                    else:
                        chapter_title = filename
                
                writer.writerow([rel_path, chapter_title])
        
        logger.info(f"✅ CSV template generated: {output_csv}")
        logger.info(f"   Title: {folder_name}")
        logger.info(f"   Output: {output_m4b}")
        logger.info(f"   Files: {len(m4b_files)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to write CSV file: {e}")
        return False


def parse_csv_input(csv_file: str) -> Tuple[List[Dict], Dict]:
    """
    Parse CSV file with optional metadata headers and file/title columns.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        Tuple of (file_list, metadata_dict)
        file_list: List of dicts with 'file' and 'title' keys
        metadata_dict: Dict with metadata from # prefixed rows
    """
    csv_file = os.path.abspath(csv_file)
    
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV file not found: {csv_file}")
    
    metadata = {}
    file_list = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Process metadata lines (starting with #)
    data_start_idx = 0
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('#'):
            # Parse metadata line: #key,value or #key: value
            if ',' in line:
                key, value = line[1:].split(',', 1)
            elif ':' in line:
                key, value = line[1:].split(':', 1)
            else:
                continue
            
            key = key.strip().lower()
            value = value.strip()
            
            if key and value:
                metadata[key] = value
            data_start_idx = i + 1
        elif line and not line.startswith('#'):
            # Found first non-metadata line
            break
    
    # Process CSV data
    csv_data = lines[data_start_idx:]
    if not csv_data:
        raise ValueError("No data rows found in CSV file")
    
    # Filter out empty lines from CSV data
    csv_data = [line for line in csv_data if line.strip()]
    
    if not csv_data:
        raise ValueError("No non-empty data rows found in CSV file")
    
    # Parse CSV data
    csv_reader = csv.DictReader(csv_data)
    
    for row in csv_reader:
        if 'file' not in row:
            raise ValueError("CSV must have a 'file' column")
        
        file_path = row['file'].strip()
        if not file_path:
            continue
            
        # Convert to absolute path
        if not os.path.isabs(file_path):
            # Make relative to CSV file directory
            csv_dir = os.path.dirname(csv_file)
            file_path = os.path.join(csv_dir, file_path)
        
        file_path = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            continue
            
        if Path(file_path).suffix.lower() not in {'.m4b', '.m4a'}:
            logger.warning(f"Skipping non-M4B file: {file_path}")
            continue
        
        title = row.get('title', '').strip()
        
        file_list.append({
            'file': file_path,
            'title': title
        })
    
    if not file_list:
        raise ValueError("No valid M4B files found in CSV")
    
    logger.info(f"Loaded {len(file_list)} files from CSV with {len(metadata)} metadata entries")
    
    return file_list, metadata


def combine_m4b_files(input_pattern: str = None, output_file: str = None, title: Optional[str] = None,
                     preserve_existing_chapters: bool = False, temp_dir: Optional[str] = None,
                     csv_file: Optional[str] = None) -> bool:
    """
    Combine multiple M4B files into a single M4B file with chapters.
    
    Args:
        input_pattern: Glob pattern to match M4B files (ignored if csv_file is provided)
        output_file: Output M4B file path (can be overridden by CSV metadata)
        title: Optional title for the combined audiobook (can be overridden by CSV metadata)
        preserve_existing_chapters: If True, preserve existing chapter structure within files
        temp_dir: Optional temporary directory to use (will not be removed if provided)
        csv_file: Optional CSV file with file paths and titles
        
    Returns:
        True if successful, False otherwise
    """
    if not check_ffmpeg():
        logger.error("FFmpeg is required but not available")
        return False
    
    csv_metadata = {}
    
    if csv_file:
        # Load files from CSV
        try:
            file_title_list, csv_metadata = parse_csv_input(csv_file)
            m4b_files = [item['file'] for item in file_title_list]
            
            # Override output file and title from CSV metadata if provided
            if 'output_path' in csv_metadata:
                output_file = csv_metadata['output_path']
            if 'title' in csv_metadata and not title:
                title = csv_metadata['title']
                
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Error reading CSV file: {e}")
            return False
    else:
        # Find files using glob pattern
        if not input_pattern:
            logger.error("Either input_pattern or csv_file must be provided")
            return False
            
        matching_files = glob.glob(input_pattern, recursive=True)
        m4b_files = [os.path.abspath(f) for f in matching_files if Path(f).suffix.lower() in {'.m4b', '.m4a'}]
        
        # Create file_title_list for consistency
        file_title_list = [{'file': f, 'title': ''} for f in m4b_files]
    
    if not m4b_files:
        source = "CSV file" if csv_file else f"pattern: {input_pattern}"
        logger.error(f"No M4B files found in {source}")
        return False
    
    if not output_file:
        logger.error("Output file must be specified")
        return False
    
    # Sort files naturally (handles numbers correctly)
    m4b_files.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
    
    logger.info(f"Found {len(m4b_files)} M4B files to combine:")
    for i, file_path in enumerate(m4b_files, 1):
        logger.info(f"  {i}. {os.path.basename(file_path)}")
    
    start_time = time.time()
    
    # Extract metadata from all files
    logger.info("Extracting metadata from files...")
    files_metadata = []
    total_duration = 0.0
    
    for file_path in m4b_files:
        metadata = get_audio_metadata(file_path)
        if not metadata:
            logger.error(f"Could not extract metadata from {file_path}")
            return False
        
        metadata['file_path'] = file_path
        metadata['start_offset'] = total_duration
        files_metadata.append(metadata)
        total_duration += metadata['duration']
        
        logger.info(f"  {os.path.basename(file_path)}: {format_time(metadata['duration'])}")
    
    # Check audio compatibility
    compatible = check_audio_compatibility(files_metadata)
    if compatible:
        logger.info("All files have compatible audio parameters - using stream copy")
        encode_params = ['-c', 'copy']
    else:
        logger.info("Files have different audio parameters - re-encoding to AAC")
        encode_params = ['-c:a', 'aac', '-b:a', '64k', '-ac', '2']
    
    # Generate chapters
    logger.info("Generating chapter structure...")
    chapters = []
    current_time = 0.0
    
    for i, file_meta in enumerate(files_metadata, 1):
        # Get title from CSV if available
        csv_title = ''
        if csv_file:
            # Find matching file in file_title_list
            for item in file_title_list:
                if item['file'] == file_meta['file_path']:
                    csv_title = item['title']
                    break
        
        if preserve_existing_chapters:
            # Extract existing chapters and offset them
            existing_chapters = extract_existing_chapters(file_meta['file_path'])
            if existing_chapters:
                logger.info(f"  File {i} has {len(existing_chapters)} existing chapters")
                for chapter in existing_chapters:
                    base_title = csv_title or derive_chapter_title(file_meta['file_path'], i, file_meta.get('title', ''))
                    chapters.append({
                        'title': f"{base_title} - {chapter['title']}",
                        'start': current_time + chapter['start'],
                        'end': current_time + chapter['end']
                    })
            else:
                # No existing chapters, create one for the whole file
                chapter_title = csv_title or derive_chapter_title(file_meta['file_path'], i, file_meta.get('title', ''))
                chapters.append({
                    'title': chapter_title,
                    'start': current_time,
                    'end': current_time + file_meta['duration']
                })
        else:
            # Create one chapter per file
            chapter_title = csv_title or derive_chapter_title(file_meta['file_path'], i, file_meta.get('title', ''))
            chapters.append({
                'title': chapter_title,
                'start': current_time,
                'end': current_time + file_meta['duration']
            })
        
        current_time += file_meta['duration']
    
    logger.info(f"Created {len(chapters)} chapters, total duration: {format_time(total_duration)}")
    
    # Create or use temporary directory for intermediate files
    if temp_dir:
        # Use provided temp directory and don't remove it
        temp_dir = os.path.abspath(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        temp_context = nullcontext(temp_dir)
        logger.info(f"Using provided temporary directory: {temp_dir}")
    else:
        # Create temporary directory that will be cleaned up
        temp_context = tempfile.TemporaryDirectory()
        logger.info("Creating temporary directory...")
    
    with temp_context as use_temp_dir:
        logger.info("Creating temporary files...")
        
        # Create concat file
        concat_file = create_concat_file(m4b_files, use_temp_dir)
        
        # Determine output metadata
        output_metadata = {
            'title': title or csv_metadata.get('title') or files_metadata[0].get('album', '') or 'Combined Audiobook',
            'artist': csv_metadata.get('author') or files_metadata[0].get('artist', ''),
            'album': title or csv_metadata.get('title') or files_metadata[0].get('album', '') or 'Combined Audiobook',
            'author': csv_metadata.get('author', ''),
            'narrator': csv_metadata.get('narrator', ''),
            'genre': csv_metadata.get('genre', 'Audiobook'),
            'year': csv_metadata.get('year', ''),
            'description': csv_metadata.get('description', '')
        }
        
        # Create metadata file with chapters
        metadata_file = create_chapter_metadata(chapters, use_temp_dir, output_metadata)
        
        # Handle cover art if provided
        cover_file = None
        if 'cover_path' in csv_metadata:
            cover_path = csv_metadata['cover_path']
            
            # Check if it's a URL
            if cover_path.startswith(('http://', 'https://')):
                # Download cover art from URL
                cover_file = download_cover_art(cover_path, use_temp_dir)
                if cover_file:
                    logger.info(f"Using downloaded cover art: {cover_file}")
                else:
                    logger.warning(f"Failed to download cover art from: {cover_path}")
            else:
                # Handle local file path
                if not os.path.isabs(cover_path) and csv_file:
                    # Make relative to CSV file directory
                    csv_dir = os.path.dirname(csv_file)
                    cover_path = os.path.join(csv_dir, cover_path)
                
                cover_path = os.path.abspath(cover_path)
                if os.path.exists(cover_path):
                    cover_file = cover_path
                    logger.info(f"Using cover art: {cover_path}")
                else:
                    logger.warning(f"Cover art file not found: {cover_path}")
        
        # Ensure output directory exists
        output_file = os.path.abspath(output_file)
        ensure_output_directory(output_file)
        
        # First step: Combine audio files
        logger.info("Combining audio files...")
        temp_combined = os.path.join(use_temp_dir, 'combined_temp.m4b')
        
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', concat_file
        ] + encode_params + [
            '-f', 'mp4',
            '-y',  # Overwrite output
            temp_combined
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("Audio files combined successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to combine audio files: {e.stderr}")
            return False
        
        # Second step: Add metadata and chapters
        logger.info("Adding chapter metadata...")
        
        cmd = [
            'ffmpeg', '-i', temp_combined,
            '-i', metadata_file
        ]
        
        # Add cover art if provided
        if cover_file:
            cmd.extend(['-i', cover_file])
            cmd.extend(['-map', '0', '-map', '2', '-map_metadata', '1'])
            cmd.extend(['-disposition:v:0', 'attached_pic'])
        else:
            cmd.extend(['-map_metadata', '1'])
        
        cmd.extend([
            '-c', 'copy',
            '-f', 'mp4',
            '-y',  # Overwrite output
            output_file
        ])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("Metadata and chapters added successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to add metadata: {e.stderr}")
            return False
        
        # Verify output file
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            total_time = time.time() - start_time
            logger.info(
                f"✅ Successfully created {output_file} "
                f"({file_size_mb:.1f}MB) with {len(chapters)} chapters "
                f"in {format_time(total_time)}"
            )
            return True
        else:
            logger.error("Output file was not created or is empty")
            return False