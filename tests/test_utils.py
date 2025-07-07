"""
Tests for M4B Tools utility functions.
"""

import pytest
import tempfile
import os
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path

from m4b_tools.utils import (
    format_time, check_ffmpeg, natural_sort_key, 
    get_audio_metadata, get_audio_duration, ensure_output_directory
)


class TestUtils:
    """Test utility functions."""
    
    def test_format_time(self):
        """Test time formatting function."""
        assert format_time(30) == "30s"
        assert format_time(90) == "1m 30s"
        assert format_time(3661) == "1h 1m 1s"
        assert format_time(3600) == "1h 0m 0s"
        assert format_time(0) == "0s"
    
    @patch('subprocess.run')
    def test_check_ffmpeg_success(self, mock_run):
        """Test FFmpeg check when FFmpeg is available."""
        mock_run.return_value = MagicMock()
        assert check_ffmpeg() is True
        assert mock_run.call_count == 2  # Called for both ffmpeg and ffprobe
    
    @patch('subprocess.run')
    def test_check_ffmpeg_failure(self, mock_run):
        """Test FFmpeg check when FFmpeg is not available."""
        mock_run.side_effect = FileNotFoundError()
        assert check_ffmpeg() is False
    
    def test_natural_sort_key(self):
        """Test natural sorting key function."""
        filenames = ["file10.m4b", "file2.m4b", "file1.m4b", "file20.m4b"]
        sorted_names = sorted(filenames, key=natural_sort_key)
        expected = ["file1.m4b", "file2.m4b", "file10.m4b", "file20.m4b"]
        assert sorted_names == expected
    
    @patch('subprocess.run')
    def test_get_audio_metadata_success(self, mock_run):
        """Test getting audio metadata when successful."""
        mock_result = MagicMock()
        mock_result.stdout = '{"format": {"duration": "123.45", "tags": {"title": "Test"}}, "streams": [{"codec_type": "audio", "codec_name": "aac", "channels": 2}]}'
        mock_run.return_value = mock_result
        
        metadata = get_audio_metadata("test.m4b")
        assert metadata['duration'] == 123.45
        assert metadata['title'] == "Test"
        assert metadata['codec'] == "aac"
        assert metadata['channels'] == 2
    
    @patch('subprocess.run')
    def test_get_audio_metadata_failure(self, mock_run):
        """Test getting audio metadata when it fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'ffprobe')
        
        metadata = get_audio_metadata("nonexistent.m4b")
        assert metadata == {}
    
    @patch('subprocess.run')
    def test_get_audio_duration_success(self, mock_run):
        """Test getting audio duration when successful."""
        mock_result = MagicMock()
        mock_result.stdout = "123.456\n"
        mock_run.return_value = mock_result
        
        duration = get_audio_duration("test.m4b")
        assert duration == 123.456
    
    @patch('subprocess.run')
    def test_get_audio_duration_failure(self, mock_run):
        """Test getting audio duration when it fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'ffprobe')
        
        duration = get_audio_duration("nonexistent.m4b")
        assert duration is None
    
    def test_ensure_output_directory(self):
        """Test ensuring output directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "subdir", "test.m4b")
            
            # Directory should not exist initially
            assert not os.path.exists(os.path.dirname(test_file))
            
            # Call function
            ensure_output_directory(test_file)
            
            # Directory should now exist
            assert os.path.exists(os.path.dirname(test_file))
    
    def test_ensure_output_directory_existing(self):
        """Test ensuring output directory when it already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.m4b")
            
            # Directory already exists
            assert os.path.exists(os.path.dirname(test_file))
            
            # Should not raise an error
            ensure_output_directory(test_file)