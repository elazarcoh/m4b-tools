import csv
import sys
from pathlib import Path
from .splitter import extract_chapters_from_m4b

def dump_m4b_metadata(file_path: str, format: str = 'csv', output_file: str = None) -> int:
    """
    Dump M4B metadata in CSV format.
    Args:
        file_path: Path to the M4B file
        format: Only 'csv' is supported (default: 'csv')
        output_file: Optional output file path (writes to stdout if None)
    Returns:
        0 on success, 1 on error
    """
    try:
        if format and format != 'csv':
            print("Error: Only 'csv' format is supported for metadata export", file=sys.stderr)
            return 1
        chapters, metadata = extract_chapters_from_m4b(file_path)
        fieldnames = [
            'file', 'chapter_num', 'chapter_title', 'chapter_start', 'chapter_end', 'chapter_duration',
            'title', 'author', 'album', 'album_artist', 'narrator', 'genre', 'year', 'codec', 'bitrate', 'sample_rate', 'channels'
        ]
        rows = []
        for c in chapters:
            row = {
                'file': str(Path(file_path).name),
                'chapter_num': c.index,
                'chapter_title': c.title,
                'chapter_start': c.start,
                'chapter_end': c.end,
                'chapter_duration': c.duration,
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'album': metadata.get('album', ''),
                'album_artist': metadata.get('album_artist', ''),
                'narrator': metadata.get('narrator', ''),
                'genre': metadata.get('genre', ''),
                'year': metadata.get('year', ''),
                'codec': metadata.get('codec', ''),
                'bitrate': metadata.get('bitrate', ''),
                'sample_rate': metadata.get('sample_rate', ''),
                'channels': metadata.get('channels', ''),
            }
            rows.append(row)
        if output_file is not None:
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return 0
    except Exception as e:
        print(f"Error dumping metadata: {e}", file=sys.stderr)
        return 1
