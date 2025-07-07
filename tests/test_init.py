"""
Tests for M4B Tools package initialization and imports.
"""

import pytest
from m4b_tools import (
    __version__, 
    convert_to_m4b, 
    convert_all_to_m4b,
    combine_m4b_files,
    generate_csv_from_folder,
    check_ffmpeg,
    format_time
)


class TestPackageInit:
    """Test package initialization and exports."""
    
    def test_version(self):
        """Test that version is defined."""
        assert __version__ == "1.0.0"
    
    def test_api_functions_importable(self):
        """Test that all API functions can be imported."""
        # These should not raise ImportError
        assert callable(convert_to_m4b)
        assert callable(convert_all_to_m4b)
        assert callable(combine_m4b_files)
        assert callable(generate_csv_from_folder)
        assert callable(check_ffmpeg)
        assert callable(format_time)
    
    def test_api_functions_have_docstrings(self):
        """Test that API functions have docstrings."""
        assert convert_to_m4b.__doc__ is not None
        assert convert_all_to_m4b.__doc__ is not None
        assert combine_m4b_files.__doc__ is not None
        assert generate_csv_from_folder.__doc__ is not None
        assert check_ffmpeg.__doc__ is not None
        assert format_time.__doc__ is not None