"""
Functionality tests for M4B Tools - testing actual audio conversion and merging.

These tests create real audio files and test the actual functionality
of converting and combining audio files.
"""

import pytest
import tempfile
import os
import subprocess
import shutil
from pathlib import Path

from m4b_tools.converter import convert_to_m4b, convert_all_to_m4b
from m4b_tools.combiner import combine_m4b_files, generate_csv_from_folder
from m4b_tools.splitter import split_m4b_file, split_multiple_m4b_files
from m4b_tools.utils import check_ffmpeg, get_audio_metadata


class TestAudioFunctionality:
    """Test actual audio conversion and merging functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Check if FFmpeg is available
        if not check_ffmpeg():
            pytest.skip("FFmpeg not available, skipping functionality tests")
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp(prefix="m4b_test_")
        self.test_files = []
        yield
        
        # Cleanup
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_audio_file(self, filename: str, duration: float = 2.0, 
                              format_name: str = "mp3", sample_rate: int = 22050) -> str:
        """
        Create a test audio file using FFmpeg.
        
        Args:
            filename: Name of the file (without extension)
            duration: Duration in seconds
            format_name: Audio format (mp3, flac, m4a, etc.)
            sample_rate: Sample rate for the audio
            
        Returns:
            Full path to the created file
        """
        output_path = os.path.join(self.temp_dir, f"{filename}.{format_name}")
        
        # Generate a simple sine wave audio file
        cmd = [
            'ffmpeg', '-f', 'lavfi', 
            '-i', f'sine=frequency=440:duration={duration}:sample_rate={sample_rate}',
            '-ac', '1',  # Mono channel
            '-y',  # Overwrite if exists
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.test_files.append(output_path)
            return output_path
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to create test audio file {output_path}: {e.stderr}")
    
    def verify_audio_file(self, file_path: str, expected_duration: float = None, 
                         tolerance: float = 0.5) -> dict:
        """
        Verify that an audio file exists and has expected properties.
        
        Args:
            file_path: Path to the audio file
            expected_duration: Expected duration in seconds (optional)
            tolerance: Tolerance for duration comparison
            
        Returns:
            Audio metadata dictionary
        """
        assert os.path.exists(file_path), f"Audio file does not exist: {file_path}"
        assert os.path.getsize(file_path) > 0, f"Audio file is empty: {file_path}"
        
        metadata = get_audio_metadata(file_path)
        assert metadata is not None, f"Could not extract metadata from: {file_path}"
        
        if expected_duration is not None:
            actual_duration = metadata.get('duration', 0)
            assert abs(actual_duration - expected_duration) <= tolerance, \
                f"Duration mismatch: expected ~{expected_duration}s, got {actual_duration}s"
        
        return metadata
    
    def test_convert_single_mp3_to_m4b(self):
        """Test converting a single MP3 file to M4B."""
        # Create a test MP3 file
        mp3_file = self.create_test_audio_file("test_audio", duration=3.0, format_name="mp3")
        
        # Define output path
        output_file = os.path.join(self.temp_dir, "output.m4b")
        
        # Convert the file
        result = convert_to_m4b(mp3_file, output_file)
        
        # Verify conversion was successful
        assert result is True, "Conversion should have succeeded"
        
        # Verify output file properties
        metadata = self.verify_audio_file(output_file, expected_duration=3.0)
        
        # Verify it's actually an M4B file
        assert Path(output_file).suffix.lower() == '.m4b'
        assert metadata.get('codec') is not None
    
    def test_convert_single_flac_to_m4b(self):
        """Test converting a single FLAC file to M4B."""
        # Create a test FLAC file
        flac_file = self.create_test_audio_file("test_audio", duration=2.5, format_name="flac")
        
        # Define output path
        output_file = os.path.join(self.temp_dir, "output.m4b")
        
        # Convert the file
        result = convert_to_m4b(flac_file, output_file)
        
        # Verify conversion was successful
        assert result is True, "Conversion should have succeeded"
        
        # Verify output file properties
        self.verify_audio_file(output_file, expected_duration=2.5)
    
    def test_convert_all_multiple_files(self):
        """Test converting multiple audio files using convert_all_to_m4b."""
        # Create multiple test files in different formats
        files_created = []
        files_created.append(self.create_test_audio_file("file1", duration=2.0, format_name="mp3"))
        files_created.append(self.create_test_audio_file("file2", duration=1.5, format_name="flac"))
        files_created.append(self.create_test_audio_file("file3", duration=2.5, format_name="m4a"))
        
        # Create output directory
        output_dir = os.path.join(self.temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert all files
        pattern = os.path.join(self.temp_dir, "*")
        successful, total = convert_all_to_m4b(pattern, output_dir, preserve_structure=False)
        
        # Verify results
        assert total == 3, f"Expected 3 files, found {total}"
        assert successful == 3, f"Expected 3 successful conversions, got {successful}"
        
        # Verify each output file
        expected_outputs = ["file1.m4b", "file2.m4b", "file3.m4b"]
        for filename in expected_outputs:
            output_path = os.path.join(output_dir, filename)
            self.verify_audio_file(output_path)
    
    def test_convert_all_with_preserve_structure(self):
        """Test converting files while preserving directory structure."""
        # Create subdirectory structure
        subdir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)
        
        # Create files in different locations
        file1 = self.create_test_audio_file("root_file", duration=2.0, format_name="mp3")
        
        # Create file in subdirectory
        sub_file_path = os.path.join(subdir, "sub_file.mp3")
        cmd = [
            'ffmpeg', '-f', 'lavfi', 
            '-i', 'sine=frequency=220:duration=1.5:sample_rate=22050',
            '-ac', '1', '-y', sub_file_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        self.test_files.append(sub_file_path)
        
        # Create output directory
        output_dir = os.path.join(self.temp_dir, "output")
        
        # Convert all files with structure preservation
        pattern = os.path.join(self.temp_dir, "**", "*.mp3")
        successful, total = convert_all_to_m4b(pattern, output_dir, preserve_structure=True)
        
        # Verify results
        assert total == 2, f"Expected 2 files, found {total}"
        assert successful == 2, f"Expected 2 successful conversions, got {successful}"
        
        # Verify structure preservation
        root_output = os.path.join(output_dir, "root_file.m4b")
        sub_output = os.path.join(output_dir, "subdir", "sub_file.m4b")
        
        self.verify_audio_file(root_output)
        self.verify_audio_file(sub_output)
    
    def test_combine_m4b_files(self):
        """Test combining multiple M4B files into one."""
        # First, create some M4B files
        m4b_files = []
        durations = [2.0, 1.5, 2.5]
        
        for i, duration in enumerate(durations, 1):
            # Create source audio file
            source_file = self.create_test_audio_file(f"source{i}", duration=duration, format_name="mp3")
            
            # Convert to M4B
            m4b_file = os.path.join(self.temp_dir, f"chapter{i}.m4b")
            result = convert_to_m4b(source_file, m4b_file)
            assert result is True, f"Failed to create M4B file {i}"
            m4b_files.append(m4b_file)
        
        # Define output file
        combined_output = os.path.join(self.temp_dir, "combined.m4b")
        
        # Combine the M4B files
        pattern = os.path.join(self.temp_dir, "chapter*.m4b")
        result = combine_m4b_files(
            input_pattern=pattern,
            output_file=combined_output,
            title="Test Audiobook"
        )
        
        # Verify combination was successful
        assert result is True, "Combination should have succeeded"
        
        # Verify combined file properties
        expected_total_duration = sum(durations)
        metadata = self.verify_audio_file(combined_output, expected_duration=expected_total_duration, tolerance=1.0)
        
        # Verify it's a proper M4B file
        assert Path(combined_output).suffix.lower() == '.m4b'
    
    def test_combine_with_csv_file(self):
        """Test combining M4B files using a CSV configuration file."""
        # Create M4B files
        m4b_files = []
        for i in range(1, 4):
            source_file = self.create_test_audio_file(f"chapter{i}", duration=2.0, format_name="mp3")
            m4b_file = os.path.join(self.temp_dir, f"chapter{i}.m4b")
            result = convert_to_m4b(source_file, m4b_file)
            assert result is True
            m4b_files.append(m4b_file)
        
        # Create CSV file
        csv_file = os.path.join(self.temp_dir, "book.csv")
        combined_output = os.path.join(self.temp_dir, "combined_book.m4b")
        
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("#title,Test Book\n")
            f.write("#author,Test Author\n")
            f.write("#genre,Fiction\n")
            f.write(f"#output_path,{combined_output}\n")
            f.write("\n")
            f.write("file,title\n")
            f.write(f"{os.path.relpath(m4b_files[0], self.temp_dir)},Chapter One\n")
            f.write(f"{os.path.relpath(m4b_files[1], self.temp_dir)},Chapter Two\n")
            f.write(f"{os.path.relpath(m4b_files[2], self.temp_dir)},Chapter Three\n")
        
        # Combine using CSV
        result = combine_m4b_files(csv_file=csv_file)
        
        # Verify combination was successful
        assert result is True, "CSV-based combination should have succeeded"
        
        # Verify combined file
        self.verify_audio_file(combined_output, expected_duration=6.0, tolerance=1.0)
    
    def test_generate_csv_from_folder(self):
        """Test generating a CSV template from a folder of M4B files."""
        # Create M4B files
        for i in range(1, 4):
            source_file = self.create_test_audio_file(f"part{i:02d}", duration=1.5, format_name="mp3")
            m4b_file = os.path.join(self.temp_dir, f"part{i:02d}.m4b")
            result = convert_to_m4b(source_file, m4b_file)
            assert result is True
        
        # Generate CSV
        csv_output = os.path.join(self.temp_dir, "generated.csv")
        result = generate_csv_from_folder(self.temp_dir, csv_output)
        
        # Verify CSV generation was successful
        assert result is True, "CSV generation should have succeeded"
        assert os.path.exists(csv_output), "CSV file should exist"
        
        # Verify CSV contents
        with open(csv_output, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check for metadata headers
            assert "#title," in content
            assert "#output_path," in content
            
            # Check for file entries
            assert "part01.m4b" in content
            assert "part02.m4b" in content
            assert "part03.m4b" in content
            assert "file,title" in content
    
    def test_generate_csv_from_multiple_folders_glob_pattern(self):
        """Test generating CSV templates from multiple folders using glob patterns."""
        # Create multiple test folders with M4B files
        test_folders = ["book1", "book2", "series_book3"]
        
        for folder_name in test_folders:
            folder_path = os.path.join(self.temp_dir, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            
            # Create 2-3 M4B files in each folder
            num_files = 2 if folder_name == "book1" else 3
            for i in range(1, num_files + 1):
                source_file = self.create_test_audio_file(f"{folder_name}_part{i:02d}", duration=1.5, format_name="mp3")
                m4b_file = os.path.join(folder_path, f"part{i:02d}.m4b")
                result = convert_to_m4b(source_file, m4b_file)
                assert result is True
        
        # Test with simple wildcard pattern
        pattern = os.path.join(self.temp_dir, "book*")
        result = generate_csv_from_folder(pattern)
        assert result is True, "CSV generation with glob pattern should succeed"
        
        # Verify individual CSV files were created
        for folder_name in test_folders:
            if folder_name.startswith("book"):
                csv_file = os.path.join(self.temp_dir, folder_name, f"{folder_name}.csv")
                assert os.path.exists(csv_file), f"CSV file should exist for {folder_name}"
                
                # Verify CSV content
                with open(csv_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    assert "#title," in content
                    assert "#output_path," in content
                    assert "file,title" in content
    
    def test_generate_csv_from_multiple_folders_recursive_pattern(self):
        """Test generating CSV templates with recursive glob patterns."""
        # Create nested folder structure
        base_folders = ["series1", "series2"]
        
        for series in base_folders:
            series_path = os.path.join(self.temp_dir, series)
            os.makedirs(series_path, exist_ok=True)
            
            # Create sub-folders within each series
            for book_num in range(1, 3):
                book_folder = f"book{book_num}"
                book_path = os.path.join(series_path, book_folder)
                os.makedirs(book_path, exist_ok=True)
                
                # Create M4B files in each book folder
                for i in range(1, 3):
                    source_file = self.create_test_audio_file(f"{series}_{book_folder}_part{i:02d}", duration=1.5, format_name="mp3")
                    m4b_file = os.path.join(book_path, f"chapter{i:02d}.m4b")
                    result = convert_to_m4b(source_file, m4b_file)
                    assert result is True
        
        # Test with recursive pattern
        pattern = os.path.join(self.temp_dir, "**/book*")
        result = generate_csv_from_folder(pattern)
        assert result is True, "CSV generation with recursive pattern should succeed"
        
        # Verify CSV files were created for each book folder
        for series in base_folders:
            for book_num in range(1, 3):
                book_folder = f"book{book_num}"
                csv_file = os.path.join(self.temp_dir, series, book_folder, f"{book_folder}.csv")
                assert os.path.exists(csv_file), f"CSV file should exist for {series}/{book_folder}"
    
    def test_generate_csv_multiple_folders_no_matches(self):
        """Test glob pattern that matches no directories."""
        # Test with pattern that won't match anything
        pattern = os.path.join(self.temp_dir, "nonexistent_*")
        result = generate_csv_from_folder(pattern)
        assert result is False, "CSV generation should fail when no directories match"
    
    def test_generate_csv_multiple_folders_empty_directories(self):
        """Test with directories that contain no M4B files."""
        # Create empty directories
        empty_folders = ["empty1", "empty2"]
        for folder_name in empty_folders:
            folder_path = os.path.join(self.temp_dir, folder_name)
            os.makedirs(folder_path, exist_ok=True)
        
        # Test with pattern matching empty directories
        pattern = os.path.join(self.temp_dir, "empty*")
        result = generate_csv_from_folder(pattern)
        assert result is False, "CSV generation should fail when directories have no M4B files"
    
    def test_generate_csv_mixed_folders_some_with_files(self):
        """Test with a mix of folders - some with M4B files, some empty."""
        # Create folder with M4B files
        good_folder = os.path.join(self.temp_dir, "good_book")
        os.makedirs(good_folder, exist_ok=True)
        
        for i in range(1, 3):
            source_file = self.create_test_audio_file(f"good_part{i:02d}", duration=1.5, format_name="mp3")
            m4b_file = os.path.join(good_folder, f"part{i:02d}.m4b")
            result = convert_to_m4b(source_file, m4b_file)
            assert result is True
        
        # Create empty folder
        empty_folder = os.path.join(self.temp_dir, "empty_book")
        os.makedirs(empty_folder, exist_ok=True)
        
        # Test with pattern matching both folders
        pattern = os.path.join(self.temp_dir, "*_book")
        result = generate_csv_from_folder(pattern)
        assert result is True, "CSV generation should succeed if at least one folder has files"
        
        # Verify CSV was created for the good folder
        csv_file = os.path.join(good_folder, "good_book.csv")
        assert os.path.exists(csv_file), "CSV file should exist for folder with M4B files"
        
        # Verify no CSV was created for the empty folder
        empty_csv_file = os.path.join(empty_folder, "empty_book.csv")
        assert not os.path.exists(empty_csv_file), "CSV file should not exist for empty folder"
    
    def test_generate_csv_single_folder_vs_glob_behavior(self):
        """Test that single folder path works the same as before."""
        # Create M4B files in a single folder
        single_folder = os.path.join(self.temp_dir, "single_test")
        os.makedirs(single_folder, exist_ok=True)
        
        for i in range(1, 4):
            source_file = self.create_test_audio_file(f"single_part{i:02d}", duration=1.5, format_name="mp3")
            m4b_file = os.path.join(single_folder, f"part{i:02d}.m4b")
            result = convert_to_m4b(source_file, m4b_file)
            assert result is True
        
        # Test with direct folder path (no glob patterns)
        result = generate_csv_from_folder(single_folder)
        assert result is True, "CSV generation for single folder should work"
        
        # Verify CSV was created
        csv_file = os.path.join(single_folder, "single_test.csv")
        assert os.path.exists(csv_file), "CSV file should exist"
        
        # Verify content is correct
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "#title," in content
            assert "#output_path," in content
            assert "part01.m4b" in content
            assert "part02.m4b" in content
            assert "part03.m4b" in content
    
    def test_generate_csv_with_custom_output_ignored_for_glob(self):
        """Test that custom output path is ignored when using glob patterns."""
        # Create multiple folders
        test_folders = ["test_book1", "test_book2"]
        
        for folder_name in test_folders:
            folder_path = os.path.join(self.temp_dir, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            
            # Create M4B files
            for i in range(1, 3):
                source_file = self.create_test_audio_file(f"{folder_name}_part{i:02d}", duration=1.5, format_name="mp3")
                m4b_file = os.path.join(folder_path, f"part{i:02d}.m4b")
                result = convert_to_m4b(source_file, m4b_file)
                assert result is True
        
        # Test with glob pattern and custom output (should be ignored)
        pattern = os.path.join(self.temp_dir, "test_book*")
        custom_output = os.path.join(self.temp_dir, "custom.csv")
        result = generate_csv_from_folder(pattern, custom_output)
        assert result is True, "CSV generation should succeed"
        
        # Verify custom output file was NOT created
        assert not os.path.exists(custom_output), "Custom output should be ignored for glob patterns"
        
        # Verify individual CSV files were created instead
        for folder_name in test_folders:
            csv_file = os.path.join(self.temp_dir, folder_name, f"{folder_name}.csv")
            assert os.path.exists(csv_file), f"CSV file should exist for {folder_name}"

    def test_generate_csv_folder_with_subdirectories(self):
        """Test CSV generation from folder containing M4B files in subdirectories."""
        # Create main folder with nested structure
        main_folder = os.path.join(self.temp_dir, "audiobook")
        os.makedirs(main_folder, exist_ok=True)
        
        # Create M4B files in root of main folder
        for i in range(1, 3):
            source_file = self.create_test_audio_file(f"root_part{i:02d}", duration=1.5, format_name="mp3")
            m4b_file = os.path.join(main_folder, f"part{i:02d}.m4b")
            result = convert_to_m4b(source_file, m4b_file)
            assert result is True
        
        # Create subdirectory with more M4B files
        sub_folder = os.path.join(main_folder, "bonus_content")
        os.makedirs(sub_folder, exist_ok=True)
        
        for i in range(1, 3):
            source_file = self.create_test_audio_file(f"bonus_part{i:02d}", duration=1.5, format_name="mp3")
            m4b_file = os.path.join(sub_folder, f"bonus{i:02d}.m4b")
            result = convert_to_m4b(source_file, m4b_file)
            assert result is True
        
        # Generate CSV for main folder (should include files from subdirectories)
        result = generate_csv_from_folder(main_folder)
        assert result is True, "CSV generation should succeed"
        
        # Verify CSV was created
        csv_file = os.path.join(main_folder, "audiobook.csv")
        assert os.path.exists(csv_file), "CSV file should exist"
        
        # Verify content includes files from subdirectories
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "part01.m4b" in content, "Root level files should be included"
            assert "part02.m4b" in content, "Root level files should be included"
            assert "bonus_content" in content, "Subdirectory files should be included"
            assert "bonus01.m4b" in content, "Subdirectory files should be included"
            assert "bonus02.m4b" in content, "Subdirectory files should be included"