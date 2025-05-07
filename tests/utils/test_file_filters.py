import pytest
from utils.file_filters import is_valid_media_file, is_valid_directory, sanitize_filename

@pytest.mark.parametrize("filename,expected", [
    ("episode1.mkv", True),
    ("sample_episode1.mkv", False),
    ("screens_episode1.mkv", False),
    ("episode1.jpg", False),
    ("Thumbs.db", False),
    ("randomfile.txt", True),
    ("photo.JPG", False),
    ("video.SFV", False),
    ("screens_movie.mp4", False),
    ("good_movie.mkv", True),
    ("anime_episode01.mp4", True),
    ("this/isa/path/to/a/file.mp4", True),
    ("/this/isanother/path/to/a/file.png", False),
    ("/this/is/another/path/to/a/file.JPG", False),
])
def test_is_valid_media_file(filename, expected):
    assert is_valid_media_file(filename) == expected

@pytest.mark.parametrize("dirname,expected", [
    ("valid_folder", True),
    ("screenshots_folder", False),
    ("Sample_Folder", False),
    ("regular_folder", True),
    (".DS_Store", False),
    ("sample_folder", False),
    ("screens_folder", False),
    ("anime_folder", True),
    ("Random_Folder", True),
    ("anime_folder/episode1.mp4", True),
    ("anime_folder/screenshots", False),
    ("anime_folder/sample_episode1.mkv", False),
])
def test_is_valid_directory(dirname, expected):
    assert is_valid_directory(dirname) == expected

@pytest.mark.parametrize("name,expected", [
    ("ValidName", "ValidName"),
    ("Invalid/Name", "InvalidName"),
    ("Bad<Name>Test", "BadNameTest"),
    ("Weird|Name*Chars?", "WeirdNameChars"),
])
def test_sanitize_filename(name, expected):
    assert sanitize_filename(name) == expected