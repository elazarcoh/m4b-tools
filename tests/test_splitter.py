"""
Unit tests for the M4B splitter module.

These tests focus on the specific functionality of the splitter module,
including filename sanitization, template formatting, and chapter extraction.
"""

import pytest
import tempfile
import os
import shutil
from unittest.mock import patch

from m4b_tools.splitter import (
    sanitize_filename, format_chapter_filename, ChapterInfo, 
    extract_chapters_from_m4b, SUPPORTED_SPLIT_FORMATS, DEFAULT_TEMPLATE
)
from m4b_tools.utils import AudioMetadata


class TestSplitterModule:
    """Test the splitter module functions."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        self.temp_dir = tempfile.mkdtemp(prefix="splitter_test_")
        yield
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test basic cases
        assert sanitize_filename("simple_name") == "simple_name"
        assert sanitize_filename("name with spaces") == "name with spaces"
        
        # Test invalid characters
        assert sanitize_filename("name<>:with|invalid*chars") == "name_with_invalid_chars"
        assert sanitize_filename('name"with/quotes\\and\\slashes') == "name_with_quotes_and_slashes"
        
        # Test multiple consecutive underscores
        assert sanitize_filename("name___with___many___underscores") == "name_with_many_underscores"
        
        # Test leading/trailing whitespace and dots
        assert sanitize_filename("  .name.  ") == "name"
        
        # Test empty string
        assert sanitize_filename("") == "untitled"
        assert sanitize_filename("   ") == "untitled"
        
        # Test very long filename
        long_name = "a" * 250
        result = sanitize_filename(long_name)
        assert len(result) <= 200
    
    def test_chapter_info_class(self):
        """Test ChapterInfo class."""
        chapter = ChapterInfo("Chapter 1", 0.0, 120.0, 1)
        
        assert chapter.title == "Chapter 1"
        assert chapter.start == 0.0
        assert chapter.end == 120.0
        assert chapter.index == 1
        assert chapter.duration == 120.0
        
        # Test string representation
        repr_str = repr(chapter)
        assert "Chapter 1" in repr_str
        assert "0.00-120.00s" in repr_str
    
    def test_format_chapter_filename(self):
        """Test chapter filename formatting."""
        chapter = ChapterInfo("The Beginning", 0.0, 120.0, 1)
        metadata: AudioMetadata = {
            'title': 'My Great Book',
            'author': 'John Doe', 
            'narrator': 'Jane Smith',
            'genre': 'Fiction',
            'year': '2023'
        }
        
        # Test default template
        result = format_chapter_filename(
            DEFAULT_TEMPLATE, chapter, metadata, 'mp3', '/path/to/book.m4b'
        )
        expected = "My Great Book/01 - The Beginning.mp3"
        assert result == expected
        
        # Test custom template
        template = "{author}/{book_title}/Chapter {chapter_num:02d} - {chapter_title} [{duration_formatted}].{ext}"
        result = format_chapter_filename(
            template, chapter, metadata, 'mp3', '/path/to/book.m4b'
        )
        assert result.startswith("John Doe/My Great Book/Chapter 01 - The Beginning [2m 0s].mp3")
        
        # Test template with missing metadata
        empty_metadata: AudioMetadata = {}
        result = format_chapter_filename(
            "{author}/{book_title}.{ext}", chapter, empty_metadata, 'mp3', '/path/to/book.m4b'
        )
        assert result == "/book.mp3"  # Falls back to filename
        
        # Test invalid template variable (should fall back to default)
        with patch('m4b_tools.splitter.logger') as mock_logger:
            result = format_chapter_filename(
                "{invalid_variable}.{ext}", chapter, metadata, 'mp3', '/path/to/book.m4b'
            )
            expected_default = "My Great Book/01 - The Beginning.mp3"
            assert result == expected_default
            mock_logger.warning.assert_called_once()
    
    def test_supported_formats(self):
        """Test that supported formats are defined correctly."""
        expected_formats = {'.mp3', '.m4a', '.m4b', '.aac', '.ogg', '.flac'}
        assert SUPPORTED_SPLIT_FORMATS == expected_formats
    
    @patch('m4b_tools.splitter.subprocess.run')
    @patch('m4b_tools.splitter.get_audio_metadata')
    def test_extract_chapters_from_m4b_with_chapters(self, mock_get_metadata, mock_subprocess):
        """Test extracting chapters from M4B with existing chapters."""
        # Mock ffprobe output with chapters
        mock_subprocess.return_value.stdout = '''
        {
            "chapters": [
                {
                    "start_time": "0.000000",
                    "end_time": "120.000000",
                    "tags": {"title": "Chapter 1"}
                },
                {
                    "start_time": "120.000000", 
                    "end_time": "240.000000",
                    "tags": {"title": "Chapter 2"}
                }
            ]
        }
        '''
        
        mock_get_metadata.return_value = {'title': 'Test Book', 'duration': 240.0}
        
        chapters, metadata = extract_chapters_from_m4b('/path/to/test.m4b')
        
        assert len(chapters) == 2
        assert chapters[0].title == "Chapter 1"
        assert chapters[0].start == 0.0
        assert chapters[0].end == 120.0
        assert chapters[0].index == 1
        assert chapters[1].title == "Chapter 2"
        assert chapters[1].start == 120.0
        assert chapters[1].end == 240.0
        assert chapters[1].index == 2
        
        assert metadata.get('title') == 'Test Book'
    
    @patch('m4b_tools.splitter.subprocess.run')
    @patch('m4b_tools.splitter.get_audio_metadata')
    def test_extract_chapters_from_m4b_no_chapters(self, mock_get_metadata, mock_subprocess):
        """Test extracting from M4B with no chapters (creates single chapter)."""
        # Mock ffprobe output with no chapters
        mock_subprocess.return_value.stdout = '{"chapters": []}'
        
        mock_get_metadata.return_value = {'title': 'Single Chapter Book', 'duration': 180.0}
        
        chapters, metadata = extract_chapters_from_m4b('/path/to/test.m4b')
        
        assert len(chapters) == 1
        assert chapters[0].title == "Single Chapter Book"
        assert chapters[0].start == 0.0
        assert chapters[0].end == 180.0
        assert chapters[0].index == 1
    
    @patch('m4b_tools.splitter.subprocess.run')
    def test_extract_chapters_error_handling(self, mock_subprocess):
        """Test error handling in chapter extraction."""
        # Mock subprocess error
        mock_subprocess.side_effect = Exception("FFprobe failed")
        
        chapters, metadata = extract_chapters_from_m4b('/path/to/invalid.m4b')
        
        assert chapters == []
        assert metadata == {}
    
    def test_default_template_constant(self):
        """Test that the default template is properly defined."""
        assert DEFAULT_TEMPLATE == "{book_title}/{chapter_num:02d} - {chapter_title}.{ext}"
        
        # Test that it contains all expected variables
        expected_vars = ['{book_title}', '{chapter_num:02d}', '{chapter_title}', '{ext}']
        for var in expected_vars:
            assert var in DEFAULT_TEMPLATE
