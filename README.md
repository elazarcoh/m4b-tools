# M4B Tools

A collection of Python scripts for converting audio files to M4B format and combining M4B files with chapters. This project was generated using Vibe Coding and serves as practice for using GitHub Copilot's agent mode.

## Prerequisites

- **FFmpeg**: Required for audio conversion and processing
  ```bash
  # Ubuntu/Debian
  sudo apt install ffmpeg
  
  # macOS (with Homebrew)
  brew install ffmpeg
  
  # Windows (with Chocolatey)
  choco install ffmpeg
  ```

- **Python 3.7+** with the following optional dependencies:
  ```bash
  pip install tqdm  # For progress bars
  ```

## Scripts Overview

### 1. convert-all-to-m4b.py

Converts various audio formats to M4B format while preserving directory structure. Supports batch conversion with parallel processing.

**Supported Input Formats:**
- MP3 (.mp3)
- FLAC (.flac)
- M4A (.m4a)
- AAC (.aac)
- OGG (.ogg)
- WAV (.wav)
- WMA (.wma)

**Usage:**
```bash
python convert-all-to-m4b.py [options] pattern output_dir
```

**Arguments:**
- `pattern`: Glob pattern to match audio files (e.g., "**/*.mp3" or "/path/to/books/**/*.flac")
- `output_dir`: Output base directory for converted M4B files

**Options:**
- `--base-input-path, -b`: Base input path for determining relative directory structure
- `--flat`: Save all files in output directory without preserving structure
- `--verbose, -v`: Enable verbose logging
- `--progress-bar, -p`: Show a visual progress bar (requires tqdm)
- `--jobs, -j`: Number of parallel FFmpeg processes (default: 1)

**Examples:**
```bash
# Convert all MP3 files in current directory, preserving structure
python convert-all-to-m4b.py "**/*.mp3" ./output

# Convert with custom base path and progress bar
python convert-all-to-m4b.py "**/*.flac" ./converted -b /path/to/audiobooks -p

# Convert with parallel processing (4 concurrent jobs)
python convert-all-to-m4b.py "books/**/*.mp3" ./m4b_output -j 4

# Convert to flat structure (all files in one directory)
python convert-all-to-m4b.py "**/*.flac" ./output --flat
```

### 2. combine-m4b-chapters.py

Combines multiple M4B files into a single M4B file with chapters. Each input file becomes a chapter in the output file.

**Usage:**
```bash
python combine-m4b-chapters.py {combine,generate-csv} [options]
```

#### Commands:

##### `combine` - Combine M4B files
```bash
python combine-m4b-chapters.py combine [options] pattern output_file
```

**Arguments:**
- `pattern`: Glob pattern to match M4B files (ignored if --csv is used)
- `output_file`: Output M4B file path (can be overridden by CSV metadata)

**Options:**
- `--title, -t`: Title for the combined audiobook
- `--preserve-chapters, -p`: Preserve existing chapter structure within individual files
- `--verbose, -v`: Enable verbose logging
- `--temp-dir`: Temporary directory for intermediate files
- `--csv`: CSV file with file paths, titles, and metadata

**Examples:**
```bash
# Combine all M4B files in current directory
python combine-m4b-chapters.py combine "*.m4b" complete_book.m4b

# Combine with custom title
python combine-m4b-chapters.py combine "parts/*.m4b" "complete_book.m4b" --title "The Complete Book"

# Preserve existing chapters within files
python combine-m4b-chapters.py combine "**/*.m4b" combined.m4b --preserve-chapters

# Use CSV file for advanced metadata control
python combine-m4b-chapters.py combine --csv book_files.csv
```

##### `generate-csv` - Generate CSV template
```bash
python combine-m4b-chapters.py generate-csv [options] folder
```

**Arguments:**
- `folder`: Path to folder containing M4B files

**Options:**
- `--output, -o`: Output CSV file path (defaults to folder_name.csv)
- `--verbose, -v`: Enable verbose logging

**Examples:**
```bash
# Generate CSV template from folder
python combine-m4b-chapters.py generate-csv /path/to/audiobook/folder

# Generate with custom output path
python combine-m4b-chapters.py generate-csv /path/to/folder --output my_book.csv
```

#### CSV Format for Advanced Metadata

The CSV format allows you to specify detailed metadata and chapter titles:

```csv
# Metadata rows (optional, start with #):
#title,My Audiobook Title
#author,Author Name
#narrator,Narrator Name
#genre,Fiction
#year,2024
#description,Book description
#output_path,/path/to/output.m4b
#cover_path,cover.jpg

# Data rows:
file,title
chapter01.m4b,Introduction
chapter02.m4b,The Beginning
chapter03.m4b,The Middle
chapter04.m4b,The End
```

**Cover Art Support:**
- Local files: `#cover_path,/path/to/cover.jpg`
- URLs: `#cover_path,https://example.com/cover.jpg`

## Workflow Examples

### Converting and Combining Audiobooks

1. **Convert multiple audio formats to M4B:**
   ```bash
   python convert-all-to-m4b.py "audiobooks/**/*.mp3" ./m4b_files -p -j 4
   ```

2. **Generate CSV template for combination:**
   ```bash
   python combine-m4b-chapters.py generate-csv ./m4b_files
   ```

3. **Edit the generated CSV file to add metadata and chapter titles**

4. **Combine into final audiobook:**
   ```bash
   python combine-m4b-chapters.py combine --csv m4b_files.csv
   ```

### Quick Conversion and Combination

```bash
# Convert all FLAC files to M4B
python convert-all-to-m4b.py "book_chapters/*.flac" ./temp_m4b

# Combine into single audiobook
python combine-m4b-chapters.py combine "temp_m4b/*.m4b" final_book.m4b --title "Complete Audiobook"
```

## Features

### convert-all-to-m4b.py Features:
- ✅ Batch conversion of multiple audio formats
- ✅ Directory structure preservation
- ✅ Parallel processing support
- ✅ Progress tracking with visual progress bars
- ✅ Comprehensive logging
- ✅ File size and duration reporting
- ✅ Automatic output directory creation
- ✅ Skip existing files

### combine-m4b-chapters.py Features:
- ✅ Chapter creation from individual files
- ✅ Metadata preservation and enhancement
- ✅ CSV-based configuration
- ✅ Cover art support (local files and URLs)
- ✅ Existing chapter structure preservation
- ✅ Audio compatibility checking
- ✅ Automatic re-encoding when needed
- ✅ Comprehensive metadata support
- ✅ Natural filename sorting

## Audio Quality Settings

Both scripts are optimized for audiobook content:
- **Bitrate**: 64k (suitable for spoken content)
- **Format**: M4B (audiobook format)
- **Channels**: Stereo (or original channel count)
- **Codec**: AAC (high compatibility)

## Troubleshooting

### Common Issues:

1. **FFmpeg not found**
   - Ensure FFmpeg is installed and in your PATH
   - Verify with: `ffmpeg -version`

2. **Permission errors**
   - Check write permissions for output directories
   - Run with appropriate permissions

3. **Memory issues with large files**
   - Reduce the number of parallel jobs (`-j` option)
   - Process files in smaller batches

4. **Progress bar not showing**
   - Install tqdm: `pip install tqdm`
   - Use `--progress-bar` or `-p` flag

### Getting Help:

```bash
# Get help for conversion script
python convert-all-to-m4b.py --help

# Get help for combination script
python combine-m4b-chapters.py --help

# Get help for specific commands
python combine-m4b-chapters.py combine --help
python combine-m4b-chapters.py generate-csv --help
```

## Project Background

This project was created using **Vibe Coding** as a practice exercise for working with **GitHub Copilot's agent mode**. It demonstrates:

- Automated code generation and refinement
- AI-assisted development workflows
- Best practices for Python CLI tools
- Audio processing with FFmpeg
- Comprehensive documentation generation

The tools are designed to be practical for audiobook enthusiasts who need to convert and organize their audio collections into the M4B format with proper chapter structure.

## License

This project is provided as-is for educational and personal use.
