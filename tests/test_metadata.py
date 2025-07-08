import csv
import pytest
from m4b_tools.metadata import dump_m4b_metadata

class DummyChapter:
    def __init__(self, index, title, start, end, duration):
        self.index = index
        self.title = title
        self.start = start
        self.end = end
        self.duration = duration

@pytest.fixture
def patch_extract_chapters(monkeypatch):
    def fake_extract_chapters_from_m4b(file_path):
        chapters = [
            DummyChapter(1, 'Intro', 0.0, 10.0, 10.0),
            DummyChapter(2, 'Chapter 1', 10.0, 70.0, 60.0),
        ]
        metadata = {
            'title': 'Book Title',
            'author': 'Author Name',
            'album': 'Album',
            'album_artist': 'Album Artist',
            'narrator': 'Narrator',
            'genre': 'Genre',
            'year': '2024',
            'codec': 'aac',
            'bitrate': '128k',
            'sample_rate': '44100',
            'channels': '2',
        }
        return chapters, metadata
    monkeypatch.setattr('m4b_tools.metadata.extract_chapters_from_m4b', fake_extract_chapters_from_m4b)

def test_dump_m4b_metadata_csv(tmp_path, patch_extract_chapters):
    out_file = tmp_path / 'meta.csv'
    ret = dump_m4b_metadata('dummy.m4b', format='csv', output_file=str(out_file))
    assert ret == 0
    with open(out_file, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2
    assert rows[0]['chapter_title'] == 'Intro'
    assert rows[1]['chapter_title'] == 'Chapter 1'
    assert rows[0]['author'] == 'Author Name'
    assert rows[1]['author'] == 'Author Name'
    assert rows[0]['file'] == 'dummy.m4b'

def test_dump_m4b_metadata_default_csv(tmp_path, patch_extract_chapters):
    out_file = tmp_path / 'meta.csv'
    # format omitted, should default to csv
    ret = dump_m4b_metadata('dummy.m4b', output_file=str(out_file))
    assert ret == 0
    with open(out_file, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2
    assert rows[0]['chapter_title'] == 'Intro'
    assert rows[1]['chapter_title'] == 'Chapter 1'

def test_dump_m4b_metadata_invalid_format(tmp_path, patch_extract_chapters):
    out_file = tmp_path / 'meta.csv'
    ret = dump_m4b_metadata('dummy.m4b', format='ffmpeg', output_file=str(out_file))
    assert ret == 1
    assert not out_file.exists()
