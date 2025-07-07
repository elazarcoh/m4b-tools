"""
Command-line interface for M4B Tools.

Provides a unified entry point for all M4B tools functionality:
- convert: Convert audio files to M4B format
- combine: Combine M4B files with chapters
- generate-csv: Generate CSV template from M4B files
"""

import argparse
import logging
import sys
from typing import Optional

from . import __version__
from .converter import convert_all_to_m4b
from .combiner import combine_m4b_files, generate_csv_from_folder


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def cmd_convert(args) -> int:
    """Handle the convert command."""
    setup_logging(args.verbose)
    
    # Validate jobs argument
    if args.jobs < 1:
        print("Error: Number of jobs must be at least 1", file=sys.stderr)
        return 1
    
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
        return 0
    else:
        print(f"⚠️  {successful}/{total} files converted successfully")
        return 1 if successful == 0 else 0


def cmd_combine(args) -> int:
    """Handle the combine command."""
    setup_logging(args.verbose)
    
    # Validate arguments
    if not args.csv and not args.pattern:
        print("Error: Either pattern or --csv must be provided", file=sys.stderr)
        return 1
    
    if not args.csv and not args.output:
        print("Error: Output file must be specified when not using CSV", file=sys.stderr)
        return 1
    
    # Combine files
    success = combine_m4b_files(
        input_pattern=args.pattern,
        output_file=args.output,
        title=args.title,
        preserve_existing_chapters=args.preserve_chapters,
        temp_dir=args.temp_dir,
        csv_file=args.csv
    )
    
    if success:
        output_name = args.output or "output from CSV"
        print(f"✅ Successfully combined M4B files into {output_name}")
        return 0
    else:
        print("❌ Failed to combine M4B files")
        return 1


def cmd_generate_csv(args) -> int:
    """Handle the generate-csv command."""
    setup_logging(args.verbose)
    
    # Generate CSV template
    success = generate_csv_from_folder(args.folder, args.output)
    if success:
        print("✅ CSV template generated successfully")
        return 0
    else:
        print("❌ Failed to generate CSV template")
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        description="M4B Tools - Convert and combine audio files in M4B format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert audio files to M4B
  m4b-tools convert "**/*.mp3" ./output
  m4b-tools convert "books/**/*.flac" ./converted -p -j 4
  
  # Generate CSV template for combining
  m4b-tools generate-csv ./m4b_files
  
  # Combine M4B files using pattern
  m4b-tools combine "*.m4b" output.m4b --title "My Book"
  
  # Combine M4B files using CSV
  m4b-tools combine --csv book_files.csv
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'M4B Tools {__version__}'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Convert command
    convert_parser = subparsers.add_parser(
        'convert',
        help='Convert audio files to M4B format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert all MP3 files preserving structure
  m4b-tools convert "**/*.mp3" ./output
  
  # Convert with custom base path and progress bar
  m4b-tools convert "**/*.flac" ./converted -b /path/to/audiobooks -p
  
  # Convert with parallel processing (4 concurrent jobs)
  m4b-tools convert "books/**/*.mp3" ./m4b_output -j 4
  
  # Convert to flat structure (all files in one directory)
  m4b-tools convert "**/*.flac" ./output --flat
        """
    )
    
    convert_parser.add_argument(
        'pattern', 
        help='Glob pattern to match audio files (e.g., "**/*.mp3" or "/path/to/books/**/*.flac")'
    )
    convert_parser.add_argument(
        'output_dir',
        help='Output base directory for converted M4B files'
    )
    convert_parser.add_argument(
        '--base-input-path', '-b',
        help='Base input path for determining relative directory structure'
    )
    convert_parser.add_argument(
        '--flat',
        action='store_true',
        help='Save all files in output directory without preserving structure'
    )
    convert_parser.add_argument(
        '--progress-bar', '-p',
        action='store_true',
        help='Show a visual progress bar (requires tqdm: pip install tqdm)'
    )
    convert_parser.add_argument(
        '--jobs', '-j',
        type=int,
        default=1,
        help='Number of parallel FFmpeg processes (default: 1)'
    )
    
    # Combine command
    combine_parser = subparsers.add_parser(
        'combine',
        help='Combine M4B files into a single file with chapters',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Combine all M4B files in current directory
  m4b-tools combine "*.m4b" output.m4b
  
  # Combine files with custom title
  m4b-tools combine "book_parts/*.m4b" "complete_book.m4b" --title "The Complete Book"
  
  # Preserve existing chapter structure within files
  m4b-tools combine "**/*.m4b" combined.m4b --preserve-chapters
  
  # Use CSV file for advanced metadata control
  m4b-tools combine --csv book_files.csv
        """
    )
    
    combine_parser.add_argument(
        'pattern',
        nargs='?',
        help='Glob pattern to match M4B files (e.g., "*.m4b" or "parts/*.m4b")'
    )
    combine_parser.add_argument(
        'output',
        nargs='?',
        help='Output M4B file path'
    )
    combine_parser.add_argument(
        '--csv',
        help='CSV file with file paths, titles, and metadata'
    )
    combine_parser.add_argument(
        '--title',
        help='Title for the combined audiobook'
    )
    combine_parser.add_argument(
        '--preserve-chapters',
        action='store_true',
        help='Preserve existing chapter structure within individual files'
    )
    combine_parser.add_argument(
        '--temp-dir',
        help='Use specified temporary directory (will not be removed)'
    )
    
    # Generate CSV command
    csv_parser = subparsers.add_parser(
        'generate-csv',
        help='Generate a CSV template from a folder containing M4B files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate CSV template from current directory
  m4b-tools generate-csv .
  
  # Generate CSV template from specific folder
  m4b-tools generate-csv /path/to/m4b_files
  
  # Generate CSV template with custom output path
  m4b-tools generate-csv ./books ./my_template.csv
        """
    )
    
    csv_parser.add_argument(
        'folder',
        help='Folder containing M4B files'
    )
    csv_parser.add_argument(
        'output',
        nargs='?',
        help='Output CSV file path (default: folder_name.csv in the source folder)'
    )
    
    return parser


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'convert':
            return cmd_convert(args)
        elif args.command == 'combine':
            return cmd_combine(args)
        elif args.command == 'generate-csv':
            return cmd_generate_csv(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())