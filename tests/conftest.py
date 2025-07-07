"""
Pytest configuration and shared fixtures.
"""

import pytest
import tempfile
import os


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def sample_audio_files(temp_dir):
    """Create sample audio files for testing."""
    files = []
    for i in range(3):
        file_path = os.path.join(temp_dir, f"sample{i+1}.mp3")
        # Create empty files for testing
        with open(file_path, 'w') as f:
            f.write("")
        files.append(file_path)
    return files