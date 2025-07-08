# M4B Tools

A Python package for converting audio files to M4B format, combining M4B files with chapters, and splitting M4B files by chapters. This package provides both a command-line interface and a programmatic API for comprehensive audiobook management.

---

**About this project:**  
This project is a (successful!) experiment in using AI to generate an entire Python package from scratch. All code, documentation, and design were created with the help of GitHub Copilot (both Agent mode in VSCode and the coding agent on GitHub web), without manual coding. The process demonstrates the power and practicality of modern AI tools for real-world software development.

---

## Quick Start

Install using pipx for an isolated command-line tool:

```bash
pipx install m4b-tools
```

Or install using pip:

```bash
pip install m4b-tools
```

### Prerequisites

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

### Basic Usage

```bash
# Convert audio files to M4B
m4b-tools convert "*.mp3" ./output

# Combine M4B files with chapters
m4b-tools combine "*.m4b" combined.m4b --title "My Audiobook"

# Split M4B file by chapters
m4b-tools split audiobook.m4b ./chapters
```

## API Usage

Use M4B Tools in your Python code:

```python
import m4b_tools

# Convert a single file
success = m4b_tools.convert_to_m4b("input.mp3", "output.m4b")

# Batch convert files with progress
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

# Split M4B file by chapters
success = m4b_tools.split_m4b_file(
    "audiobook.m4b",
    "./chapters",
    output_format="mp3"
)

# Generate CSV template for metadata
success = m4b_tools.generate_csv_from_folder("./m4b_files")
```

## Development

This project uses [Hatch](https://hatch.pypa.io/) for development environment management.

### Installation for Development

```bash
# Install hatch
pip install hatch

# Clone the repository
git clone https://github.com/elazarcoh/m4b-tools.git
cd m4b-tools

# Create and enter development environment
hatch shell
```

### Running Tests

```bash
# Run all tests
hatch run test

# Run tests with coverage report
hatch run cov

# View coverage report (after running 'hatch run cov')
# Opens HTML report: htmlcov/index.html
```

The coverage configuration is set up to:
- Track coverage for the `src/m4b_tools` package
- Generate both terminal and HTML reports
- Exclude common utility lines from coverage analysis

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

# Dump M4B metadata as CSV (one row per chapter, all metadata repeated per row)
m4b-tools metadata audiobook.m4b --output metadata.csv
```

## Advanced API Usage

For more complex use cases, the API provides additional options:

```python
import m4b_tools

# Advanced conversion with custom options
successful, total = m4b_tools.convert_all_to_m4b(
    input_pattern="audiobooks/**/*.flac",
    output_dir="./converted",
    base_input_path="/path/to/audiobooks",  # Preserve directory structure
    flat_output=False,  # Keep nested folders
    show_progress_bar=True,
    max_workers=4,
    verbose=True
)

# Combine with CSV metadata file
success = m4b_tools.combine_m4b_files(
    csv_file="metadata.csv",  # Advanced metadata control
    preserve_chapters=True,   # Keep existing chapters
    temp_dir="./temp"
)

# Split with custom naming template
success = m4b_tools.split_m4b_file(
    input_file="audiobook.m4b",
    output_dir="./chapters",
    output_format="flac",
    naming_template="{author}/{book_title}/Chapter {chapter_num:02d} - {chapter_title}.{ext}",
    max_workers=4
)
```

## CSV Format for Advanced Metadata

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

## Features

### Conversion Features:
- ✅ Convert various audio formats (MP3, FLAC, M4A, AAC, OGG, WAV, WMA) to M4B
- ✅ Batch conversion with parallel processing
- ✅ Preserve directory structure or flatten output
- ✅ Progress bars and verbose logging

### Combination Features:
- ✅ Combine multiple M4B files into a single audiobook
- ✅ Chapter-based organization
- ✅ Advanced CSV metadata control
- ✅ Cover art support (local files and URLs)
- ✅ Preserve existing chapter structure

### Splitting Features:
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
