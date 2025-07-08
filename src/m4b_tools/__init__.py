"""
M4B Tools - Audio conversion and chapter combination utilities.

This package provides tools for:
- Converting various audio formats to M4B (audiobook) format
- Combining multiple M4B files into a single file with chapters
- Splitting M4B files by chapters into various formats
- Generating CSV templates for metadata management

Main functions:
- convert_to_m4b: Convert a single audio file to M4B format
- convert_all_to_m4b: Batch convert multiple audio files to M4B format
- combine_m4b_files: Combine multiple M4B files into one with chapters
- split_m4b_file: Split an M4B file by chapters into various formats
- split_multiple_m4b_files: Split multiple M4B files by chapters
- generate_csv_from_folder: Generate CSV template from M4B files in a folder
"""

__version__ = "1.0.0"
__author__ = "M4B Tools Contributors"

# Import main functions for API access
from .converter import convert_to_m4b, convert_all_to_m4b
from .combiner import combine_m4b_files, generate_csv_from_folder
from .splitter import split_m4b_file, split_multiple_m4b_files
from .utils import check_ffmpeg, format_time

__all__ = [
    "convert_to_m4b",
    "convert_all_to_m4b", 
    "combine_m4b_files",
    "split_m4b_file",
    "split_multiple_m4b_files",
    "generate_csv_from_folder",
    "check_ffmpeg",
    "format_time",
]