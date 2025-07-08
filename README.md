# M4B Tools

A Python package for converting audio files to M4B format, combining M4B files with chapters, and splitting M4B files by chapters. This package provides both a command-line interface and a programmatic API for comprehensive audiobook management.

## Installation

Install from source using pip:

```bash
pip install .
```

For development installation:

```bash
pip install -e .
```

For installation with optional dependencies:

```bash
pip install .[progress]  # Includes tqdm for progress bars
pip install .[test]      # Includes test dependencies
```

### pipx Installation

For isolated installation as a command-line tool:

```bash
pipx install .
```

## Prerequisites

- **Python 3.7+**: Required for the package
- **FFmpeg**: Required for audio conversion and processing
  ```bash
  # Ubuntu/Debian
  sudo apt install ffmpeg
  
  # macOS (with Homebrew)
  brew install ffmpeg
  
  # Windows (with Chocolatey)
  choco install ffmpeg
  ```

## Command-Line Interface

After installation, use the `m4b-tools` command:

```bash
# Show help
m4b-tools --help

# Convert audio files to M4B
m4b-tools convert "**/*.mp3" ./output
m4b-tools convert "books/**/*.flac" ./converted -p -j 4

# Generate CSV template for combining
m4b-tools generate-csv ./m4b_files

# Combine M4B files using pattern
m4b-tools combine "*.m4b" output.m4b --title "My Book"

# Combine M4B files using CSV
m4b-tools combine --csv book_files.csv

# Split M4B files by chapters
m4b-tools split "*.m4b" ./output_chapters
```

## Programmatic API

Use M4B Tools in your Python code:

```python
import m4b_tools

# Convert a single file
success = m4b_tools.convert_to_m4b("input.mp3", "output.m4b")

# Batch convert files
successful, total = m4b_tools.convert_all_to_m4b(
    "**/*.mp3", 
    "./output",
    show_progress_bar=True,
    max_workers=4
)

# Combine M4B files
success = m4b_tools.combine_m4b_files(
    input_pattern="*.m4b",
    output_file="combined.m4b",
    title="My Audiobook"
)

# Generate CSV template
success = m4b_tools.generate_csv_from_folder("./m4b_files")
```

## Legacy Scripts (Deprecated)

The original scripts are still available but deprecated. Use the `m4b-tools` command instead.

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

##### `split` - Split M4B files by chapters
```bash
m4b-tools split [options] pattern output_dir
```

**Arguments:**
- `pattern`: Glob pattern to match M4B files (e.g., "*.m4b" or "audiobook.m4b")
- `output_dir`: Output directory for split chapter files

**Options:**
- `--format, -f`: Output format for chapter files (choices: mp3, m4a, m4b, aac, ogg, flac, default: mp3)
- `--template, -t`: Naming template for output files (default: `{book_title}/{chapter_num:02d} - {chapter_title}.{ext}`)
- `--jobs, -j`: Number of parallel chapter extraction processes (default: 1)
- `--verbose, -v`: Enable verbose logging

**Template Variables:**
- `{book_title}`: Book title from metadata or filename
- `{author}`: Author from metadata
- `{narrator}`: Narrator from metadata
- `{chapter_num}`: Chapter number (1-based)
- `{chapter_title}`: Chapter title
- `{genre}`: Genre from metadata
- `{year}`: Publication year from metadata
- `{original_filename}`: Original M4B filename (without extension)
- `{duration}`: Chapter duration (e.g., "120s")
- `{duration_formatted}`: Formatted duration (e.g., "2m 0s")
- `{ext}`: Output file extension

**Examples:**
```bash
# Split a single M4B file by chapters to MP3
m4b-tools split "audiobook.m4b" ./output_chapters

# Split multiple M4B files to M4A format
m4b-tools split "*.m4b" ./chapters --format m4a

# Split with custom naming template and nested folders
m4b-tools split "book.m4b" ./output --template "{author}/{book_title}/Chapter {chapter_num:02d} - {chapter_title}.{ext}"

# Split with parallel processing for faster extraction
m4b-tools split "**/*.m4b" ./output -j 4

# Split to different formats
m4b-tools split "audiobook.m4b" ./flac_chapters --format flac
m4b-tools split "audiobook.m4b" ./m4b_chapters --format m4b
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

### Splitting Audiobooks by Chapters

1. **Split a single M4B audiobook into MP3 chapters:**
   ```bash
   m4b-tools split "complete_audiobook.m4b" ./chapters
   ```

2. **Split multiple audiobooks with custom naming:**
   ```bash
   m4b-tools split "*.m4b" ./split_books --template "{author}/{book_title}/Part {chapter_num:02d} - {chapter_title}.{ext}"
   ```

3. **Convert chapters to different formats:**
   ```bash
   # Split to high-quality FLAC
   m4b-tools split "audiobook.m4b" ./flac_chapters --format flac
   
   # Split to M4A for Apple devices
   m4b-tools split "audiobook.m4b" ./m4a_chapters --format m4a
   ```

4. **Parallel processing for large files:**
   ```bash
   m4b-tools split "large_audiobook.m4b" ./chapters --jobs 4
   ```

### m4b-tools split Features:
- ✅ Split M4B files by chapters into multiple formats
- ✅ Support for MP3, M4A, M4B, AAC, OGG, and FLAC output
- ✅ Flexible naming templates with metadata variables
- ✅ Nested directory structure support
- ✅ Metadata preservation in split files
- ✅ Parallel chapter extraction for performance
- ✅ Automatic filename sanitization
- ✅ Chapter detection from M4B files
- ✅ Fallback to single chapter for files without chapters
- ✅ Comprehensive error handling and logging
