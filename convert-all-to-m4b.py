#!/usr/bin/env python3
"""
Audio to M4B Converter

This script converts audio files to M4B format while preserving directory structure.
It supports various input formats and uses FFmpeg for conversion.
"""

import os
import glob
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supported audio formats
SUPPORTED_FORMATS = {'.mp3', '.flac', '.m4a', '.aac', '.ogg', '.wav', '.wma'}

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

def check_ffmpeg():
    """Check if FFmpeg is available in the system."""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("FFmpeg is not installed or not found in PATH")
        return False

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

def convert_to_m4b(input_file: str, output_file: str) -> bool:
    """
    Convert an audio file to M4B format using FFmpeg.
    
    Args:
        input_file: Path to the input audio file
        output_file: Path to the output M4B file
        
    Returns:
        True if conversion was successful, False otherwise
    """
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # FFmpeg command for M4B conversion
        cmd = [
            'ffmpeg', '-i', input_file,
            '-b:a', '64k',  # Audio bitrate (good for audiobooks)
            '-vn', # Disable video
            '-y',           # Overwrite output file
            output_file
        ]
        
        logger.info(f"Converting: {os.path.basename(input_file)} -> {os.path.basename(output_file)}")
        conversion_start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        conversion_time = time.time() - conversion_start
        
        # Verify the output file was created
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            logger.info(
                f"✅ Converted {os.path.basename(output_file)} "
                f"({file_size_mb:.1f}MB) in {format_time(conversion_time)}"
            )
            return True
        else:
            logger.error(f"Output file not created or is empty: {output_file}")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error converting {input_file}: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error converting {input_file}: {str(e)}")
        return False

def process_single_file(input_file: str, output_base_path: Path, preserve_structure: bool,
                       base_input_path: Optional[str], base_path: Optional[Path], 
                       glob_pattern: str) -> tuple[bool, str]:
    """
    Process a single audio file conversion.
    
    Returns:
        Tuple of (success, input_file_path)
    """
    input_path = Path(input_file)
    
    if preserve_structure:
        # Determine relative path based on base_input_path or pattern
        if base_input_path and base_path:
            # Use base_input_path as the reference point
            try:
                relative_path = input_path.relative_to(base_path)
            except ValueError:
                # If file is not under base_path, use filename only
                logger.warning(f"File {input_file} is not under base_input_path {base_input_path}, using filename only")
                relative_path = input_path.name
        else:
            # Legacy behavior: derive base from glob pattern
            if '**' in glob_pattern:
                pattern_base = glob_pattern.split('**')[0].rstrip('/')
                if pattern_base:
                    try:
                        relative_path = input_path.relative_to(pattern_base)
                    except ValueError:
                        # If relative_to fails, use the filename only
                        relative_path = input_path.name
                else:
                    # Pattern starts with **, use absolute path relative to cwd
                    try:
                        relative_path = input_path.relative_to(Path.cwd())
                    except ValueError:
                        relative_path = input_path.name
            else:
                # Simple pattern, just use filename
                relative_path = input_path.name
        
        # Create output path with M4B extension
        output_path = output_base_path / Path(relative_path).with_suffix('.m4b')
    else:
        # Flat structure - all files in output base directory
        output_filename = input_path.stem + '.m4b'
        output_path = output_base_path / output_filename
    
    # Skip if output file already exists
    if output_path.exists():
        logger.info(f"Skipping {input_file} - output already exists")
        return False, input_file
    
    # Convert the file
    success = convert_to_m4b(str(input_path), str(output_path))
    return success, input_file

def convert_all_to_m4b(glob_pattern: str, output_base_dir: str, 
                      preserve_structure: bool = True, show_progress_bar: bool = False,
                      base_input_path: Optional[str] = None, max_workers: int = 1) -> tuple[int, int]:
    """
    Convert all audio files matching a glob pattern to M4B format.
    
    Args:
        glob_pattern: Glob pattern to match audio files (e.g., "**/*.mp3")
        output_base_dir: Base directory where converted files will be saved
        preserve_structure: Whether to preserve the original directory structure
        show_progress_bar: Whether to show a visual progress bar (requires tqdm)
        base_input_path: Optional base input path for determining relative structure.
                        If provided, the glob pattern is treated as relative to this path
        max_workers: Maximum number of concurrent FFmpeg processes (default: 1)
        
    Returns:
        Tuple of (successful_conversions, total_files)
    """
    if not check_ffmpeg():
        logger.error("FFmpeg is required but not available")
        return 0, 0
    
    # Handle base input path
    if base_input_path:
        base_path = Path(base_input_path).resolve()
        # Make glob pattern relative to base input path
        if not os.path.isabs(glob_pattern):
            full_pattern = str(base_path / glob_pattern)
        else:
            full_pattern = glob_pattern
            logger.warning("Glob pattern is absolute, base_input_path will be used for structure only")
    else:
        full_pattern = glob_pattern
        base_path = None
    
    # Find all matching files
    matching_files = sorted(glob.glob(full_pattern, recursive=True))
    
    # Filter for supported audio formats
    audio_files = [
        f for f in matching_files 
        if Path(f).suffix.lower() in SUPPORTED_FORMATS
    ]
    
    if not audio_files:
        logger.warning(f"No supported audio files found matching pattern: {glob_pattern}")
        return 0, 0
    
    logger.info(f"Found {len(audio_files)} audio files to convert")
    
    # Try to import tqdm for progress bar if requested
    progress_bar = None
    if show_progress_bar:
        try:
            from tqdm import tqdm
            progress_bar = tqdm(total=len(audio_files), desc="Converting", unit="file")
        except ImportError:
            logger.warning("tqdm not installed, falling back to text progress")
            show_progress_bar = False
    
    # Create output base directory
    output_base_path = Path(output_base_dir)
    output_base_path.mkdir(parents=True, exist_ok=True)
    
    successful_conversions = 0
    total_files = len(audio_files)
    start_time = time.time()
    
    logger.info(f"Starting conversion of {total_files} files with {max_workers} worker(s)...")
    
    # Thread-safe counter for successful conversions
    success_lock = threading.Lock()
    successful_conversions = 0
    completed_files = 0
    
    def update_counters(success: bool):
        nonlocal successful_conversions, completed_files
        with success_lock:
            completed_files += 1
            if success:
                successful_conversions += 1
    
    def update_progress(input_file: str):
        """Update progress bar and log progress information."""
        # Update progress bar if available
        if progress_bar:
            with success_lock:  # Ensure thread-safe access to counters
                progress_bar.update(1)
                progress_bar.set_postfix({
                    'Success': successful_conversions,
                    'File': os.path.basename(input_file)[:30]
                })
        
        # Calculate progress and time estimates (only show if no progress bar)
        if not show_progress_bar:
            elapsed_time = time.time() - start_time
            
            with success_lock:  # Ensure thread-safe access to counters
                current_completed = completed_files
                current_successful = successful_conversions
            
            if current_completed > 0:
                avg_time_per_file = elapsed_time / current_completed
                remaining_files = total_files - current_completed
                estimated_time_remaining = avg_time_per_file * remaining_files
                
                progress_percent = (current_completed / total_files) * 100
                
                logger.info(
                    f"Progress: {current_completed}/{total_files} ({progress_percent:.1f}%) | "
                    f"Successful: {current_successful} | "
                    f"Elapsed: {format_time(elapsed_time)} | "
                    f"ETA: {format_time(estimated_time_remaining)}"
                )
    
    if max_workers == 1:
        # Single-threaded execution
        for input_file in audio_files:
            success, _ = process_single_file(
                input_file, output_base_path, preserve_structure,
                base_input_path, base_path, glob_pattern
            )
            
            update_counters(success)
            update_progress(input_file)
    else:
        # Multi-threaded execution
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(
                    process_single_file,
                    input_file, output_base_path, preserve_structure,
                    base_input_path, base_path, glob_pattern
                ): input_file for input_file in audio_files
            }
            
            # Process completed tasks
            for future in as_completed(future_to_file):
                input_file = future_to_file[future]
                try:
                    success, _ = future.result()
                    update_counters(success)
                except Exception as exc:
                    logger.error(f"File {input_file} generated an exception: {exc}")
                    update_counters(False)
                
                update_progress(input_file)
    
    # Close progress bar if it was used
    if progress_bar:
        progress_bar.close()
    
    total_time = time.time() - start_time
    logger.info(
        f"Conversion complete: {successful_conversions}/{total_files} files successfully converted "
        f"in {format_time(total_time)}"
    )
    return successful_conversions, total_files

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert audio files to M4B format while preserving directory structure"
    )
    parser.add_argument(
        'pattern', 
        help='Glob pattern to match audio files (e.g., "**/*.mp3" or "/path/to/books/**/*.flac")'
    )
    parser.add_argument(
        'output_dir',
        help='Output base directory for converted M4B files'
    )
    parser.add_argument(
        '--base-input-path', '-b',
        help='Base input path for determining relative directory structure. '
             'The glob pattern will be treated as relative to this path.'
    )
    parser.add_argument(
        '--flat', 
        action='store_true',
        help='Save all files in output directory without preserving structure'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--progress-bar', '-p',
        action='store_true',
        help='Show a visual progress bar (requires tqdm: pip install tqdm)'
    )
    parser.add_argument(
        '--jobs', '-j',
        type=int,
        default=1,
        help='Number of parallel FFmpeg processes (default: 1)'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate jobs argument
    if args.jobs < 1:
        logger.error("Number of jobs must be at least 1")
        exit(1)
    
    # Convert files
    successful, total = convert_all_to_m4b(
        args.pattern, 
        args.output_dir, 
        preserve_structure=not args.flat,
        show_progress_bar=args.progress_bar,
        base_input_path=args.base_input_path,
        max_workers=args.jobs
    )
    
    if successful == total:
        print(f"✅ All {total} files converted successfully!")
    else:
        print(f"⚠️  {successful}/{total} files converted successfully")
        exit(1)

if __name__ == "__main__":
    main()