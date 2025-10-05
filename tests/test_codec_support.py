"""
Tests for audio codec and bitrate support in M4B Tools.

These tests verify that different codecs (AAC, AAC-HE, ALAC) work correctly
and that metadata and chapters are preserved during conversion and combination.
"""

import pytest
import tempfile
import os
import subprocess
import shutil
import csv
from pathlib import Path

from m4b_tools.converter import convert_to_m4b, convert_all_to_m4b
from m4b_tools.combiner import (
    combine_m4b_files,
    generate_csv_from_folder,
    extract_existing_chapters,
)
from m4b_tools.utils import check_ffmpeg, get_audio_metadata


class TestCodecSupport:
    """Test codec and bitrate support for convert and combine commands."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Check if FFmpeg is available
        if not check_ffmpeg():
            pytest.skip("FFmpeg not available, skipping codec tests")

        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp(prefix="m4b_codec_test_")
        self.test_files = []
        yield

        # Cleanup
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_audio_file(
        self,
        filename: str,
        duration: float = 2.0,
        format_name: str = "mp3",
        sample_rate: int = 22050,
    ) -> str:
        """Create a test audio file using FFmpeg."""
        output_path = os.path.join(self.temp_dir, f"{filename}.{format_name}")

        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}:sample_rate={sample_rate}",
            "-ac",
            "1",
            "-y",
            output_path,
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.test_files.append(output_path)
            return output_path
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to create test audio file {output_path}: {e.stderr}")

    def create_test_m4b_with_metadata(
        self, filename: str, title: str = None, duration: float = 2.0
    ) -> str:
        """Create a test M4B file with metadata."""
        output_path = os.path.join(self.temp_dir, f"{filename}.m4b")

        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}:sample_rate=22050",
            "-ac",
            "1",
            "-c:a",
            "aac",
            "-b:a",
            "64k",
        ]

        if title:
            cmd.extend(["-metadata", f"title={title}"])

        cmd.extend(["-y", output_path])

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.test_files.append(output_path)
            return output_path
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to create test M4B file {output_path}: {e.stderr}")

    def verify_audio_file(
        self, file_path: str, expected_duration: float = None, tolerance: float = 0.5
    ) -> dict:
        """Verify audio file exists and has expected properties."""
        assert os.path.exists(file_path), f"Audio file does not exist: {file_path}"
        assert os.path.getsize(file_path) > 0, f"Audio file is empty: {file_path}"

        metadata = get_audio_metadata(file_path)
        assert metadata is not None, f"Could not extract metadata from: {file_path}"

        if expected_duration is not None:
            actual_duration = metadata.get("duration", 0)
            assert abs(actual_duration - expected_duration) <= tolerance, (
                f"Duration mismatch: expected ~{expected_duration}s, got {actual_duration}s"
            )

        return metadata

    # Test convert command with different codecs

    def test_convert_with_aac_codec(self):
        """Test conversion with AAC codec."""
        mp3_file = self.create_test_audio_file(
            "test_audio", duration=3.0, format_name="mp3"
        )
        output_file = os.path.join(self.temp_dir, "output_aac.m4b")

        result = convert_to_m4b(mp3_file, output_file, codec="aac", bitrate="64k")

        assert result is True, "Conversion with AAC should succeed"
        metadata = self.verify_audio_file(output_file, expected_duration=3.0)

        # Verify codec (should be AAC)
        codec = metadata.get("codec", "").lower()
        assert "aac" in codec, f"Expected AAC codec, got {codec}"

    def test_convert_with_aac_he_codec(self):
        """Test conversion with AAC-HE codec."""
        mp3_file = self.create_test_audio_file(
            "test_audio", duration=3.0, format_name="mp3"
        )
        output_file = os.path.join(self.temp_dir, "output_aac_he.m4b")

        # Note: AAC-HE requires libfdk_aac which may not be available in all FFmpeg builds
        # This test will attempt the conversion but may skip if libfdk_aac is not available
        result = convert_to_m4b(mp3_file, output_file, codec="aac_he", bitrate="48k")

        # If conversion succeeds, verify the file
        if result:
            metadata = self.verify_audio_file(output_file, expected_duration=3.0)
            # AAC-HE may fall back to regular AAC if libfdk_aac is not available
            codec = metadata.get("codec", "").lower()
            assert "aac" in codec, f"Expected AAC-based codec, got {codec}"
        else:
            pytest.skip(
                "AAC-HE encoding not available (libfdk_aac may not be installed)"
            )

    def test_convert_with_alac_codec(self):
        """Test conversion with ALAC (lossless) codec."""
        mp3_file = self.create_test_audio_file(
            "test_audio", duration=3.0, format_name="mp3"
        )
        output_file = os.path.join(self.temp_dir, "output_alac.m4b")

        # ALAC is lossless, bitrate parameter is ignored
        result = convert_to_m4b(mp3_file, output_file, codec="alac", bitrate="64k")

        assert result is True, "Conversion with ALAC should succeed"
        metadata = self.verify_audio_file(output_file, expected_duration=3.0)

        # Verify codec (should be ALAC)
        codec = metadata.get("codec", "").lower()
        assert "alac" in codec, f"Expected ALAC codec, got {codec}"

    def test_convert_with_different_bitrates(self):
        """Test conversion with different bitrates."""
        bitrates = ["32k", "64k", "128k"]

        for bitrate in bitrates:
            mp3_file = self.create_test_audio_file(
                f"test_audio_{bitrate}", duration=2.0, format_name="mp3"
            )
            output_file = os.path.join(self.temp_dir, f"output_{bitrate}.m4b")

            result = convert_to_m4b(mp3_file, output_file, codec="aac", bitrate=bitrate)

            assert result is True, f"Conversion with bitrate {bitrate} should succeed"
            self.verify_audio_file(output_file, expected_duration=2.0)

    def test_convert_all_with_codec_and_bitrate(self):
        """Test batch conversion with codec and bitrate parameters."""
        # Create multiple test files
        files_created = []
        for i in range(1, 4):
            files_created.append(
                self.create_test_audio_file(f"file{i}", duration=2.0, format_name="mp3")
            )

        # Create output directory
        output_dir = os.path.join(self.temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Convert all files with specific codec and bitrate
        pattern = os.path.join(self.temp_dir, "*.mp3")
        successful, total = convert_all_to_m4b(
            pattern, output_dir, preserve_structure=False, codec="aac", bitrate="128k"
        )

        assert total == 3, f"Expected 3 files, found {total}"
        assert successful == 3, f"Expected 3 successful conversions, got {successful}"

        # Verify each output file
        for i in range(1, 4):
            output_path = os.path.join(output_dir, f"file{i}.m4b")
            self.verify_audio_file(output_path, expected_duration=2.0)

    # Test combine command with codec and bitrate

    def test_combine_preserves_metadata(self):
        """Test that combining M4B files preserves metadata."""
        # Create M4B files with metadata
        file1 = self.create_test_m4b_with_metadata(
            "part1", title="Chapter 1", duration=2.0
        )
        file2 = self.create_test_m4b_with_metadata(
            "part2", title="Chapter 2", duration=2.0
        )

        output_file = os.path.join(self.temp_dir, "combined.m4b")

        # Combine files
        result = combine_m4b_files(
            input_pattern=os.path.join(self.temp_dir, "part*.m4b"),
            output_file=output_file,
            title="Complete Book",
        )

        assert result is True, "Combining files should succeed"

        # Verify combined file
        metadata = self.verify_audio_file(output_file, expected_duration=4.0)

        # Verify title was set
        assert metadata.get("title") == "Complete Book", "Title should be preserved"

    def test_combine_preserves_chapters(self):
        """Test that combining M4B files preserves/creates chapters."""
        # Create M4B files
        file1 = self.create_test_m4b_with_metadata(
            "part1", title="Part One", duration=2.0
        )
        file2 = self.create_test_m4b_with_metadata(
            "part2", title="Part Two", duration=2.0
        )

        output_file = os.path.join(self.temp_dir, "combined_chapters.m4b")

        # Combine files (will create chapters from files)
        result = combine_m4b_files(
            input_pattern=os.path.join(self.temp_dir, "part*.m4b"),
            output_file=output_file,
            title="Book with Chapters",
        )

        assert result is True, "Combining files should succeed"

        # Extract and verify chapters
        chapters = extract_existing_chapters(output_file)

        assert len(chapters) >= 2, (
            f"Expected at least 2 chapters, found {len(chapters)}"
        )

        # Verify chapter durations add up approximately to total duration
        total_chapter_duration = sum(ch["duration"] for ch in chapters)
        assert abs(total_chapter_duration - 4.0) <= 0.5, (
            f"Chapter durations should sum to ~4s, got {total_chapter_duration}s"
        )

    def test_combine_with_codec_parameter(self):
        """Test combining M4B files with specific codec."""
        # Create M4B files
        file1 = self.create_test_m4b_with_metadata("part1", duration=2.0)
        file2 = self.create_test_m4b_with_metadata("part2", duration=2.0)

        output_file = os.path.join(self.temp_dir, "combined_codec.m4b")

        # Combine files with specific codec
        result = combine_m4b_files(
            input_pattern=os.path.join(self.temp_dir, "part*.m4b"),
            output_file=output_file,
            codec="aac",
            bitrate="128k",
        )

        assert result is True, "Combining with codec should succeed"
        self.verify_audio_file(output_file, expected_duration=4.0)

    # Test CSV input with codec and bitrate

    def test_generate_csv_includes_codec_and_bitrate(self):
        """Test that generated CSV includes codec and bitrate columns."""
        # Create M4B files
        for i in range(1, 3):
            self.create_test_m4b_with_metadata(f"part{i:02d}", duration=1.5)

        # Generate CSV
        result = generate_csv_from_folder(self.temp_dir)
        assert result is True, "CSV generation should succeed"

        # Find and read the CSV file
        csv_files = list(Path(self.temp_dir).glob("*.csv"))
        assert len(csv_files) > 0, "CSV file should be created"

        csv_file = csv_files[0]
        with open(csv_file, "r", encoding="utf-8") as f:
            content = f.read()

            # Verify codec and bitrate metadata headers are present
            assert "#codec," in content, "CSV should include codec metadata header"
            assert "#bitrate," in content, "CSV should include bitrate metadata header"

    def test_combine_from_csv_with_codec_and_bitrate(self):
        """Test combining M4B files using CSV with codec and bitrate."""
        # Create M4B files
        file1 = self.create_test_m4b_with_metadata(
            "part1", title="Chapter 1", duration=2.0
        )
        file2 = self.create_test_m4b_with_metadata(
            "part2", title="Chapter 2", duration=2.0
        )

        # Create CSV file manually with codec and bitrate
        csv_file = os.path.join(self.temp_dir, "book.csv")
        output_file = os.path.join(self.temp_dir, "combined_from_csv.m4b")

        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            f.write("#title,Test Book\n")
            f.write("#author,Test Author\n")
            f.write(f"#output_path,{output_file}\n")
            f.write("#codec,aac\n")
            f.write("#bitrate,128k\n")
            f.write("\n")

            writer = csv.writer(f)
            writer.writerow(["file", "title", "codec", "bitrate"])
            writer.writerow([file1, "Chapter One", "aac", "128k"])
            writer.writerow([file2, "Chapter Two", "aac", "128k"])

        # Combine using CSV
        result = combine_m4b_files(csv_file=csv_file)

        assert result is True, "Combining from CSV should succeed"

        # Verify output
        metadata = self.verify_audio_file(output_file, expected_duration=4.0)
        assert metadata.get("title") == "Test Book", "Title from CSV should be used"

        # Verify chapters
        chapters = extract_existing_chapters(output_file)
        assert len(chapters) >= 2, (
            f"Expected at least 2 chapters, found {len(chapters)}"
        )
