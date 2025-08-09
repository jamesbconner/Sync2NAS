"""
Tests for the DownloadedFile model.
"""
import pytest
import datetime
import tempfile
import os
from pathlib import Path
from models.downloaded_file import DownloadedFile, FileStatus, FileType


@pytest.fixture
def sample_sftp_entry():
    """Sample SFTP entry for testing."""
    return {
        "name": "test_video.mkv",
        "path": "remote/path/test_video.mkv",
        "size": 1024000,
        "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
        "fetched_at": datetime.datetime(2024, 1, 1, 13, 0, 0),
        "is_dir": False
    }


@pytest.fixture
def sample_db_record():
    """Sample database record for testing."""
    return {
        "id": 1,
        "name": "test_video.mkv",
        "remote_path": "/incoming/test_video.mkv",
        "current_path": "/shows/Test Show/Season 01/test_video.mkv",
        "previous_path": None,
        "size": 1024000,
        "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
        "fetched_at": datetime.datetime(2024, 1, 1, 13, 0, 0),
        "is_dir": False,
        "status": "routed",
        "file_type": "video",
        "file_hash_value": "abc123",
        "file_hash_algo": "CRC32",
        "hash_calculated_at": datetime.datetime(2024, 1, 1, 12, 30, 0),
        "show_name": "Test Show",
        "season": 1,
        "episode": 1,
        "confidence": 0.95,
        "reasoning": "High confidence parsing",
        "tmdb_id": 12345,
        "routing_attempts": 1,
        "last_routing_attempt": datetime.datetime(2024, 1, 1, 14, 0, 0),
        "error_message": None,
        "metadata": '{"quality": "1080p", "codec": "h264"}'
    }


class TestDownloadedFileCreation:
    """Test DownloadedFile object creation."""

    def test_create_from_sftp_entry(self, sample_sftp_entry):
        """Test creating DownloadedFile from SFTP entry."""
        base_path = "/incoming"
        file = DownloadedFile.from_sftp_entry(sample_sftp_entry, base_path)
        
        assert file.name == "test_video.mkv"
        # remote_path should reflect the actual remote path
        assert file.remote_path == "remote/path/test_video.mkv"
        # current_path should reflect the local download destination (base_path + remote relative path)
        expected_path = str(Path("/incoming") / "remote" / "path" / "test_video.mkv")
        assert file.current_path == expected_path
        assert file.size == 1024000
        assert file.is_dir is False
        assert file.status == FileStatus.DOWNLOADED
        assert file.file_type == FileType.VIDEO

    def test_create_from_db_record(self, sample_db_record):
        """Test creating DownloadedFile from database record."""
        file = DownloadedFile.from_db_record(sample_db_record)
        
        assert file.id == 1
        assert file.name == "test_video.mkv"
        assert file.current_path == "/shows/Test Show/Season 01/test_video.mkv"
        assert file.status == FileStatus.ROUTED
        assert file.show_name == "Test Show"
        assert file.season == 1
        assert file.episode == 1
        assert file.metadata == {"quality": "1080p", "codec": "h264"}

    def test_create_with_minimal_data(self):
        """Test creating DownloadedFile with minimal required data."""
        file = DownloadedFile(
            name="test.mkv",
            original_path="/test.mkv",
            size=1000,
            modified_time=datetime.datetime.now()
        )
        
        assert file.name == "test.mkv"
        assert file.file_type == FileType.VIDEO
        assert file.status == FileStatus.DOWNLOADED
        assert file.routing_attempts == 0

    def test_file_type_auto_detection(self):
        """Test automatic file type detection from extension."""
        # Video files
        assert DownloadedFile(name="test.mkv", original_path="/test.mkv", size=1000, modified_time=datetime.datetime.now()).file_type == FileType.VIDEO
        assert DownloadedFile(name="test.mp4", original_path="/test.mp4", size=1000, modified_time=datetime.datetime.now()).file_type == FileType.VIDEO
        
        # Audio files
        assert DownloadedFile(name="test.mp3", original_path="/test.mp3", size=1000, modified_time=datetime.datetime.now()).file_type == FileType.AUDIO
        assert DownloadedFile(name="test.flac", original_path="/test.flac", size=1000, modified_time=datetime.datetime.now()).file_type == FileType.AUDIO
        
        # Subtitle files
        assert DownloadedFile(name="test.srt", original_path="/test.srt", size=1000, modified_time=datetime.datetime.now()).file_type == FileType.SUBTITLE
        assert DownloadedFile(name="test.ass", original_path="/test.ass", size=1000, modified_time=datetime.datetime.now()).file_type == FileType.SUBTITLE
        
        # Unknown files
        assert DownloadedFile(name="test.xyz", original_path="/test.xyz", size=1000, modified_time=datetime.datetime.now()).file_type == FileType.UNKNOWN


class TestDownloadedFileValidation:
    """Test DownloadedFile validation."""

    def test_negative_size_validation(self):
        """Test that negative file sizes are rejected."""
        with pytest.raises(ValueError):
            DownloadedFile(
                name="test.mkv",
                original_path="/test.mkv",
                size=-1000,
                modified_time=datetime.datetime.now()
            )

    def test_negative_season_validation(self):
        """Test that negative season numbers are rejected."""
        with pytest.raises(ValueError):
            DownloadedFile(
                name="test.mkv",
                original_path="/test.mkv",
                size=1000,
                modified_time=datetime.datetime.now(),
                season=-1
            )

    def test_negative_episode_validation(self):
        """Test that negative episode numbers are rejected."""
        with pytest.raises(ValueError):
            DownloadedFile(
                name="test.mkv",
                original_path="/test.mkv",
                size=1000,
                modified_time=datetime.datetime.now(),
                episode=-1
            )

    def test_invalid_confidence_range(self):
        """Test that confidence must be between 0.0 and 1.0."""
        with pytest.raises(ValueError):
            DownloadedFile(
                name="test.mkv",
                original_path="/test.mkv",
                size=1000,
                modified_time=datetime.datetime.now(),
                confidence=1.5
            )

    def test_invalid_tmdb_id(self):
        """Test that TMDB ID must be positive."""
        with pytest.raises(ValueError):
            DownloadedFile(
                name="test.mkv",
                original_path="/test.mkv",
                size=1000,
                modified_time=datetime.datetime.now(),
                tmdb_id=0
            )

    def test_current_path_validation(self):
        """Test that current_path cannot be the same as original_path."""
        with pytest.raises(ValueError):
            DownloadedFile(
                name="test.mkv",
                original_path="/test.mkv",
                current_path="/test.mkv",
                size=1000,
                modified_time=datetime.datetime.now()
            )


class TestDownloadedFileMethods:
    """Test DownloadedFile methods."""

    def test_to_db_tuple(self):
        """Test serialization to database tuple."""
        file = DownloadedFile(
            name="test.mkv",
            original_path="/test.mkv",
            size=1000,
            modified_time=datetime.datetime(2024, 1, 1, 12, 0, 0),
            show_name="Test Show",
            season=1,
            episode=1,
            metadata={"quality": "1080p"}
        )
        
        db_tuple = file.to_db_tuple()
        assert len(db_tuple) == 20
        assert db_tuple[0] == "test.mkv"  # name
        assert db_tuple[1] == "/test.mkv"  # original_path
        assert db_tuple[2] is None  # current_path
        assert db_tuple[3] == 1000  # size
        assert db_tuple[10] == "Test Show"  # show_name
        assert db_tuple[11] == 1  # season
        assert db_tuple[12] == 1  # episode
        assert "1080p" in db_tuple[19]  # metadata JSON

    def test_get_file_path(self):
        """Test getting the current file path."""
        file = DownloadedFile(
            name="test.mkv",
            original_path="/original/test.mkv",
            size=1000,
            modified_time=datetime.datetime.now()
        )
        
        # Should return remote_path when current_path is None
        assert file.get_file_path() == "/original/test.mkv"
        
        # Should return current_path when set
        file.current_path = "/current/test.mkv"
        assert file.get_file_path() == "/current/test.mkv"

    def test_is_media_file(self):
        """Test media file detection."""
        video_file = DownloadedFile(
            name="test.mkv",
            original_path="/test.mkv",
            size=1000,
            modified_time=datetime.datetime.now()
        )
        assert video_file.is_media_file() is True
        
        audio_file = DownloadedFile(
            name="test.mp3",
            original_path="/test.mp3",
            size=1000,
            modified_time=datetime.datetime.now()
        )
        assert audio_file.is_media_file() is True
        
        subtitle_file = DownloadedFile(
            name="test.srt",
            original_path="/test.srt",
            size=1000,
            modified_time=datetime.datetime.now()
        )
        assert subtitle_file.is_media_file() is True
        
        nfo_file = DownloadedFile(
            name="test.nfo",
            original_path="/test.nfo",
            size=1000,
            modified_time=datetime.datetime.now()
        )
        assert nfo_file.is_media_file() is False

    def test_is_video_file(self):
        """Test video file detection."""
        video_file = DownloadedFile(
            name="test.mkv",
            original_path="/test.mkv",
            size=1000,
            modified_time=datetime.datetime.now()
        )
        assert video_file.is_video_file() is True
        
        audio_file = DownloadedFile(
            name="test.mp3",
            original_path="/test.mp3",
            size=1000,
            modified_time=datetime.datetime.now()
        )
        assert audio_file.is_video_file() is False

    def test_can_be_routed(self):
        """Test routing eligibility."""
        file = DownloadedFile(
            name="test.mkv",
            original_path="/test.mkv",
            size=1000,
            modified_time=datetime.datetime.now()
        )
        
        # Should be routable by default (video file, downloaded status)
        assert file.can_be_routed() is True
        
        # Should not be routable if status is not downloaded
        file.status = FileStatus.ROUTED
        assert file.can_be_routed() is False
        
        # Should not be routable if not a media file
        file.status = FileStatus.DOWNLOADED
        file.name = "test.txt"
        assert file.can_be_routed() is False

    def test_status_transitions(self):
        """Test status transition methods."""
        file = DownloadedFile(
            name="test.mkv",
            original_path="/test.mkv",
            size=1000,
            modified_time=datetime.datetime.now()
        )
        
        # Test mark_as_processing
        file.mark_as_processing()
        assert file.status == FileStatus.PROCESSING
        assert file.routing_attempts == 1
        assert file.last_routing_attempt is not None
        
        # Test mark_as_routed
        file.mark_as_routed("/new/path/test.mkv")
        assert file.status == FileStatus.ROUTED
        assert file.current_path == "/new/path/test.mkv"
        
        # Test mark_as_error
        file.mark_as_error("Test error")
        assert file.status == FileStatus.ERROR
        assert file.error_message == "Test error"
        
        # Test reset_status
        file.reset_status()
        assert file.status == FileStatus.DOWNLOADED
        assert file.error_message is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        file = DownloadedFile(
            name="test.mkv",
            original_path="/test.mkv",
            size=1000,
            modified_time=datetime.datetime(2024, 1, 1, 12, 0, 0),
            show_name="Test Show",
            season=1,
            episode=1
        )
        
        file_dict = file.to_dict()
        assert file_dict["name"] == "test.mkv"
        assert file_dict["show_name"] == "Test Show"
        assert file_dict["season"] == 1
        assert file_dict["episode"] == 1
        assert file_dict["status"] == "downloaded"
        assert file_dict["file_type"] == "video"


class TestDownloadedFileFileOperations:
    """Test file system operations."""

    def test_exists_with_temp_file(self):
        """Test file existence check with a temporary file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            file = DownloadedFile(
                name=os.path.basename(tmp_path),
                original_path=tmp_path,
                size=0,
                modified_time=datetime.datetime.now()
            )
            
            assert file.exists() is True
            
            # Test after file is deleted
            os.unlink(tmp_path)
            assert file.exists() is False
            
        finally:
            # Clean up if file still exists
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_get_file_size(self):
        """Test getting file size."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_path = tmp_file.name
        
        try:
            file = DownloadedFile(
                name=os.path.basename(tmp_path),
                original_path=tmp_path,
                size=0,
                modified_time=datetime.datetime.now()
            )
            
            assert file.get_file_size() == 12  # "test content" is 12 bytes
            
            # Test after file is deleted
            os.unlink(tmp_path)
            assert file.get_file_size() is None
            
        finally:
            # Clean up if file still exists
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_calculate_hash(self):
        """Test hash calculation interface with different hash types and caching."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_path = tmp_file.name
        
        try:
            file = DownloadedFile(
                name=os.path.basename(tmp_path),
                original_path=tmp_path,
                size=0,
                modified_time=datetime.datetime.now()
            )
            
            # Test CRC32 hash (default) - should compute and cache
            hash_value = file.calculate_hash()
            assert hash_value is not None
            assert len(hash_value) == 8  # CRC32 hash length (8 hex chars)
            assert hash_value.isupper()  # CRC32 hashes should be uppercase
            
            # Test explicit CRC32 - should return cached value
            crc32_hash = file.calculate_hash("crc32")
            assert crc32_hash == hash_value
            
            # Test SHA256 - should compute and cache
            sha256_hash = file.calculate_hash("sha256")
            assert sha256_hash is not None
            assert len(sha256_hash) == 64  # SHA256 hash length
            
            # Test SHA256 again - should return cached value
            sha256_hash2 = file.calculate_hash("sha256")
            assert sha256_hash2 == sha256_hash
            
            # Test SHA1 - should compute and cache
            sha1_hash = file.calculate_hash("sha1")
            assert sha1_hash is not None
            assert len(sha1_hash) == 40  # SHA1 hash length
            
            # Test MD5 - should compute and cache
            md5_hash = file.calculate_hash("md5")
            assert md5_hash is not None
            assert len(md5_hash) == 32  # MD5 hash length
            
            # Test invalid hash type
            invalid_hash = file.calculate_hash("invalid")
            assert invalid_hash is None
            
            # Test update_hash method (defaults to CRC32)
            assert file.update_hash() is True
            assert file.file_hash == hash_value
            
            # Test update_hash with specific hash type
            assert file.update_hash("sha256") is True
            assert file.file_hash == sha256_hash
            
            # Test with non-existent file
            file.original_path = "/non/existent/file"
            assert file.calculate_hash() is None
            assert file.update_hash() is False
            
        finally:
            # Clean up if file still exists
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_calculate_crc32(self):
        """Test CRC32 hash calculation method."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_path = tmp_file.name
        
        try:
            file = DownloadedFile(
                name=os.path.basename(tmp_path),
                original_path=tmp_path,
                size=0,
                modified_time=datetime.datetime.now()
            )
            
            # Calculate CRC32 hash
            hash_value = file.calculate_crc32()
            assert hash_value is not None
            assert len(hash_value) == 8  # CRC32 hash length (8 hex chars)
            assert hash_value.isupper()  # CRC32 hashes should be uppercase
            
            # Test with non-existent file
            file.original_path = "/non/existent/file"
            assert file.calculate_crc32() is None
            
        finally:
            # Clean up if file still exists
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_calculate_sha256(self):
        """Test SHA256 hash calculation."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_path = tmp_file.name
        
        try:
            file = DownloadedFile(
                name=os.path.basename(tmp_path),
                original_path=tmp_path,
                size=0,
                modified_time=datetime.datetime.now()
            )
            
            # Calculate SHA256 hash
            hash_value = file.calculate_sha256()
            assert hash_value is not None
            assert len(hash_value) == 64  # SHA256 hash length
            
            # Test with non-existent file
            file.original_path = "/non/existent/file"
            assert file.calculate_sha256() is None
            
        finally:
            # Clean up if file still exists
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_calculate_sha1(self):
        """Test SHA1 hash calculation."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_path = tmp_file.name
        
        try:
            file = DownloadedFile(
                name=os.path.basename(tmp_path),
                original_path=tmp_path,
                size=0,
                modified_time=datetime.datetime.now()
            )
            
            # Calculate SHA1 hash
            hash_value = file.calculate_sha1()
            assert hash_value is not None
            assert len(hash_value) == 40  # SHA1 hash length
            
            # Test with non-existent file
            file.original_path = "/non/existent/file"
            assert file.calculate_sha1() is None
            
        finally:
            # Clean up if file still exists
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_calculate_md5(self):
        """Test MD5 hash calculation."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_path = tmp_file.name
        
        try:
            file = DownloadedFile(
                name=os.path.basename(tmp_path),
                original_path=tmp_path,
                size=0,
                modified_time=datetime.datetime.now()
            )
            
            # Calculate MD5 hash
            hash_value = file.calculate_md5()
            assert hash_value is not None
            assert len(hash_value) == 32  # MD5 hash length
            
            # Test with non-existent file
            file.original_path = "/non/existent/file"
            assert file.calculate_md5() is None
            
        finally:
            # Clean up if file still exists
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_hash_caching(self):
        """Test that hash values are properly cached."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_path = tmp_file.name
        
        try:
            file = DownloadedFile(
                name=os.path.basename(tmp_path),
                original_path=tmp_path,
                size=0,
                modified_time=datetime.datetime.now()
            )
            
            # Calculate hashes - should compute and cache
            crc32_1 = file.calculate_crc32()
            sha256_1 = file.calculate_sha256()
            sha1_1 = file.calculate_sha1()
            md5_1 = file.calculate_md5()
            
            # Calculate again - should return cached values
            crc32_2 = file.calculate_crc32()
            sha256_2 = file.calculate_sha256()
            sha1_2 = file.calculate_sha1()
            md5_2 = file.calculate_md5()
            
            # Verify cached values are returned
            assert crc32_1 == crc32_2
            assert sha256_1 == sha256_2
            assert sha1_1 == sha1_2
            assert md5_1 == md5_2
            
        finally:
            # Clean up if file still exists
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_clear_hash_cache(self):
        """Test clearing hash cache."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_path = tmp_file.name
        
        try:
            file = DownloadedFile(
                name=os.path.basename(tmp_path),
                original_path=tmp_path,
                size=0,
                modified_time=datetime.datetime.now()
            )
            
            # Calculate hashes to populate cache
            file.calculate_crc32()
            file.calculate_sha256()
            file.calculate_sha1()
            file.calculate_md5()
            
            # Verify cache is populated
            assert "crc32" in file._hash_cache
            assert "sha256" in file._hash_cache
            assert "sha1" in file._hash_cache
            assert "md5" in file._hash_cache
            
            # Clear all cache
            file.clear_hash_cache()
            
            # Verify cache is cleared
            assert len(file._hash_cache) == 0
            
        finally:
            # Clean up if file still exists
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_clear_hash_cache_for_type(self):
        """Test clearing specific hash type cache."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_path = tmp_file.name
        
        try:
            file = DownloadedFile(
                name=os.path.basename(tmp_path),
                original_path=tmp_path,
                size=0,
                modified_time=datetime.datetime.now()
            )
            
            # Calculate hashes to populate cache
            file.calculate_crc32()
            file.calculate_sha256()
            file.calculate_sha1()
            file.calculate_md5()
            
            # Clear only CRC32 cache
            file.clear_hash_cache_for_type("crc32")
            
            # Verify only CRC32 cache is cleared
            assert "crc32" not in file._hash_cache
            assert "sha256" in file._hash_cache
            assert "sha1" in file._hash_cache
            assert "md5" in file._hash_cache
            
            # Clear only SHA256 cache
            file.clear_hash_cache_for_type("sha256")
            
            # Verify only SHA256 cache is cleared
            assert "crc32" not in file._hash_cache
            assert "sha256" not in file._hash_cache
            assert "sha1" in file._hash_cache
            assert "md5" in file._hash_cache
            
        finally:
            # Clean up if file still exists
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestDownloadedFileEdgeCases:
    """Test edge cases and error handling."""

    def test_db_record_with_invalid_metadata_json(self):
        """Test handling of invalid metadata JSON in database record."""
        record = {
            "name": "test.mkv",
            "original_path": "/test.mkv",
            "size": 1000,
            "modified_time": datetime.datetime.now(),
            "fetched_at": datetime.datetime.now(),
            "is_dir": False,
            "metadata": "invalid json {"
        }
        
        # Should not raise an exception, but should log a warning
        file = DownloadedFile.from_db_record(record)
        assert file.metadata is None

    def test_empty_filename(self):
        """Test handling of empty filename."""
        with pytest.raises(ValueError):
            DownloadedFile(
                name="",
                original_path="/test.mkv",
                size=1000,
                modified_time=datetime.datetime.now()
            )

    def test_none_filename(self):
        """Test handling of None filename."""
        with pytest.raises(ValueError):
            DownloadedFile(
                name=None,
                original_path="/test.mkv",
                size=1000,
                modified_time=datetime.datetime.now()
            )

    def test_directory_file_type(self):
        """Test file type detection for directories."""
        file = DownloadedFile(
            name="test_dir",
            original_path="/test_dir",
            size=0,
            modified_time=datetime.datetime.now(),
            is_dir=True
        )
        
        assert file.file_type == FileType.UNKNOWN
        assert file.is_media_file() is False 