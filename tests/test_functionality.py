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
    
    def test_error_handling_invalid_input(self):
        """Test error handling with invalid input files."""
        # Test conversion with non-existent file
        result = convert_to_m4b("/nonexistent/file.mp3", "/tmp/output.m4b")
        assert result is False, "Conversion of non-existent file should fail"
        
        # Test conversion to invalid output path
        mp3_file = self.create_test_audio_file("test", duration=1.0, format_name="mp3")
        result = convert_to_m4b(mp3_file, "/invalid/path/output.m4b")
        assert result is False, "Conversion to invalid path should fail"
    
    @pytest.mark.parametrize("format_name", ["mp3", "flac", "m4a"])
    def test_conversion_different_formats(self, format_name):
        """Test conversion from various audio formats."""
        # Create test file
        source_file = self.create_test_audio_file(f"test_{format_name}", 
                                                duration=1.5, 
                                                format_name=format_name)
        
        # Convert to M4B
        output_file = os.path.join(self.temp_dir, f"output_{format_name}.m4b")
        result = convert_to_m4b(source_file, output_file)
        
        # Verify conversion
        assert result is True, f"Conversion from {format_name} should succeed"
        self.verify_audio_file(output_file, expected_duration=1.5)
    
    def create_test_m4b_with_chapters(self, filename: str, num_chapters: int = 3, 
                                    chapter_duration: float = 2.0) -> str:
        """
        Create a test M4B file with chapters.
        
        Args:
            filename: Name of the file (without extension)
            num_chapters: Number of chapters to create
            chapter_duration: Duration of each chapter in seconds
            
        Returns:
            Full path to the created M4B file
        """
        output_path = os.path.join(self.temp_dir, f"{filename}.m4b")
        
        # Create a longer audio file
        total_duration = num_chapters * chapter_duration
        cmd = [
            'ffmpeg', '-f', 'lavfi', 
            '-i', f'sine=frequency=440:duration={total_duration}:sample_rate=22050',
            '-ac', '1',  # Mono channel
            '-c:a', 'aac',  # Use AAC codec for M4B
            '-b:a', '64k',  # Low bitrate for test
            '-y',  # Overwrite if exists
            output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Create a chapter file for FFmpeg
            chapter_file = os.path.join(self.temp_dir, f"{filename}_chapters.txt")
            with open(chapter_file, 'w') as f:
                f.write(";FFMETADATA1\n")
                f.write("title=Test Book\n")
                f.write("album=Test Book\n") 
                f.write("artist=Test Author\n")
                f.write("\n")
                
                # Add chapter markers
                for i in range(num_chapters):
                    start_time = int(i * chapter_duration * 1000)  # Convert to milliseconds
                    end_time = int((i + 1) * chapter_duration * 1000)
                    f.write("[CHAPTER]\n")
                    f.write("TIMEBASE=1/1000\n")
                    f.write(f"START={start_time}\n")
                    f.write(f"END={end_time}\n")
                    f.write(f"title=Chapter {i + 1}\n")
                    f.write("\n")
            
            # Add chapters using FFmpeg metadata
            chapter_output = os.path.join(self.temp_dir, f"{filename}_with_chapters.m4b")
            chapter_cmd = [
                'ffmpeg', '-i', output_path, '-i', chapter_file,
                '-map_metadata', '1',  # Use metadata from chapter file
                '-c', 'copy',  # Copy streams without re-encoding
                '-y', chapter_output
            ]
            
            subprocess.run(chapter_cmd, capture_output=True, text=True, check=True)
            
            # Use the version with chapters
            os.replace(chapter_output, output_path)
            
            # Clean up chapter file
            os.remove(chapter_file)
            
            self.test_files.append(output_path)
            return output_path
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to create test M4B file {output_path}: {e.stderr}")
    
    def test_split_m4b_by_chapters(self):
        """Test splitting an M4B file by chapters."""
        # Create a test M4B file 
        m4b_file = self.create_test_m4b_with_chapters("test_book", num_chapters=3)
        
        # Create output directory
        output_dir = os.path.join(self.temp_dir, "split_output")
        
        # Split the file
        successful, total = split_m4b_file(
            file_path=m4b_file,
            output_dir=output_dir,
            output_format='mp3',
            template='{book_title}/Chapter {chapter_num:02d} - {chapter_title}.{ext}'
        )
        
        # Verify split was successful
        assert successful == total == 3, f"Expected 3 chapters split, got {successful}/{total}"
        
        # Verify output files exist
        expected_files = [
            "Test Book/Chapter 01 - Chapter 1.mp3",
            "Test Book/Chapter 02 - Chapter 2.mp3", 
            "Test Book/Chapter 03 - Chapter 3.mp3"
        ]
        
        for expected_file in expected_files:
            file_path = os.path.join(output_dir, expected_file)
            assert os.path.exists(file_path), f"Expected output file not found: {file_path}"
            assert os.path.getsize(file_path) > 0, f"Output file is empty: {file_path}"
            
            # Verify it's a valid audio file
            self.verify_audio_file(file_path, expected_duration=2.0, tolerance=1.0)
    
    def test_split_m4b_different_formats(self):
        """Test splitting M4B to different output formats."""
        # Create a test M4B file
        m4b_file = self.create_test_m4b_with_chapters("format_test", num_chapters=2)
        
        formats_to_test = ['mp3', 'm4a', 'flac']
        
        for output_format in formats_to_test:
            output_dir = os.path.join(self.temp_dir, f"split_{output_format}")
            
            # Split the file
            successful, total = split_m4b_file(
                file_path=m4b_file,
                output_dir=output_dir,
                output_format=output_format,
                template='Chapter {chapter_num:02d}.{ext}'
            )
            
            assert successful == total == 2, f"Failed to split to {output_format} format"
            
            # Verify output files
            for i in range(1, 3):
                file_path = os.path.join(output_dir, f"Chapter {i:02d}.{output_format}")
                assert os.path.exists(file_path), f"Missing {output_format} file: {file_path}"
                self.verify_audio_file(file_path, tolerance=1.5)
    
    def test_split_m4b_custom_template(self):
        """Test splitting with custom naming template."""
        # Create a test M4B file
        m4b_file = self.create_test_m4b_with_chapters("template_test", num_chapters=2)
        output_dir = os.path.join(self.temp_dir, "template_output")
        
        # Test custom template with nested folders
        template = '{author}/{book_title}/Part {chapter_num} - {chapter_title} [{duration_formatted}].{ext}'
        
        successful, total = split_m4b_file(
            file_path=m4b_file,
            output_dir=output_dir,
            output_format='mp3',
            template=template
        )
        
        assert successful == total == 2, "Failed to split with custom template"
        
        # Verify nested directory structure and files
        expected_files = [
            "Test Author/Test Book/Part 1 - Chapter 1 [2s].mp3",
            "Test Author/Test Book/Part 2 - Chapter 2 [2s].mp3"
        ]
        
        for expected_file in expected_files:
            file_path = os.path.join(output_dir, expected_file)
            assert os.path.exists(file_path), f"Expected nested file not found: {file_path}"
    
    def test_split_multiple_m4b_files(self):
        """Test splitting multiple M4B files."""
        # Create multiple test M4B files
        m4b_files = []
        for i in range(2):
            m4b_file = self.create_test_m4b_with_chapters(f"multi_book_{i}", num_chapters=2)
            m4b_files.append(m4b_file)
        
        output_dir = os.path.join(self.temp_dir, "multi_split_output")
        pattern = os.path.join(self.temp_dir, "multi_book_*.m4b")
        
        # Split multiple files
        successful_files, total_files = split_multiple_m4b_files(
            pattern=pattern,
            output_dir=output_dir,
            output_format='mp3',
            template='{original_filename}/Chapter {chapter_num:02d}.{ext}'
        )
        
        assert successful_files == total_files == 2, f"Failed to split multiple files: {successful_files}/{total_files}"
        
        # Verify all output files exist
        for i in range(2):
            for chapter in range(1, 3):
                file_path = os.path.join(output_dir, f"multi_book_{i}", f"Chapter {chapter:02d}.mp3")
                assert os.path.exists(file_path), f"Missing file: {file_path}"