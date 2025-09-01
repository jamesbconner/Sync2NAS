"""
Comprehensive validation tests for CRC32 field migration.

This module tests the migration from the generic "hash" field to the more specific
"crc32" field throughout the system, ensuring backward compatibility and proper
field handling during the transition period.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from utils.sftp_orchestrator import process_sftp_diffs
from models.downloaded_file import DownloadedFile


class TestCRC32FieldMigration:
    """Test suite for CRC32 field migration validation."""

    @pytest.fixture
    def mock_sftp_service(self, mocker):
        """Mock SFTP service for testing."""
        return mocker.Mock()

    @pytest.fixture
    def mock_db_service(self, mocker):
        """Mock database service for testing."""
        return mocker.Mock()

    @pytest.fixture
    def mock_llm_service(self, mocker):
        """Mock LLM service for testing."""
        return mocker.Mock()

    @pytest.fixture
    def sample_file_diff(self):
        """Sample file diff for testing."""
        return {
            "name": "Test.Show.S01E02.[A1B2C3D4].mkv",
            "path": "/remote/Test.Show.S01E02.[A1B2C3D4].mkv",
            "size": 100,
            "modified_time": "2024-01-01T12:00:00",
            "fetched_at": "2024-01-01T12:00:00",
            "is_dir": False,
        }

    def setup_mocks(self, mocker, tmp_path):
        """Set up common mocks for SFTP orchestrator tests."""
        # Mock file filters
        mocker.patch('utils.sftp_orchestrator.is_valid_media_file', return_value=True)
        
        # Mock ThreadPoolExecutor
        mock_executor = mocker.Mock()
        mock_future = mocker.Mock()
        mock_executor.__enter__ = mocker.Mock(return_value=mock_executor)
        mock_executor.submit.return_value = mock_future
        mock_executor.__exit__ = mocker.Mock(return_value=None)
        mocker.patch('utils.sftp_orchestrator.ThreadPoolExecutor', return_value=mock_executor)
        mocker.patch('utils.sftp_orchestrator.as_completed', return_value=[mock_future])
        mock_future.result.return_value = None
        
        # Mock SFTPService constructor
        mock_new_sftp = mocker.Mock()
        mock_new_sftp.__enter__ = mocker.Mock(return_value=mock_new_sftp)
        mock_new_sftp.__exit__ = mocker.Mock(return_value=None)
        mocker.patch('services.sftp_service.SFTPService', return_value=mock_new_sftp)
        
        return mock_executor, mock_future

    def test_crc32_field_priority_over_hash(self, tmp_path, mock_sftp_service, mock_db_service, mock_llm_service, mocker, sample_file_diff):
        """Test that 'crc32' field takes priority over 'hash' field when both are present."""
        # Setup mocks
        mock_executor, mock_future = self.setup_mocks(mocker, tmp_path)
        
        # Mock LLM to return both crc32 and hash fields
        mock_llm_service.parse_filename.return_value = {
            "show_name": "Test Show",
            "season": 1,
            "episode": 2,
            "crc32": "[A1B2C3D4]",  # This should take priority
            "hash": "[DEADBEEF]",   # This should be ignored
            "confidence": 0.95,
            "reasoning": "High confidence parsing"
        }
        
        process_sftp_diffs(
            sftp_service=mock_sftp_service,
            db_service=mock_db_service,
            diffs=[sample_file_diff],
            remote_base="/remote",
            local_base=str(tmp_path),
            dry_run=False,
            llm_service=mock_llm_service,
            parse_filenames=True,
            use_llm=True,
            llm_confidence_threshold=0.7,
        )
        
        # Verify that crc32 field was used, not hash
        assert mock_db_service.upsert_downloaded_file.call_count == 1
        upsert_arg = mock_db_service.upsert_downloaded_file.call_args[0][0]
        assert upsert_arg.file_provided_hash_value == "A1B2C3D4"  # From crc32 field

    def test_hash_field_fallback_when_crc32_missing(self, tmp_path, mock_sftp_service, mock_db_service, mock_llm_service, mocker, sample_file_diff):
        """Test that 'hash' field is used as fallback when 'crc32' field is missing."""
        # Setup mocks
        mock_executor, mock_future = self.setup_mocks(mocker, tmp_path)
        
        # Mock LLM to return only hash field (legacy format)
        mock_llm_service.parse_filename.return_value = {
            "show_name": "Test Show",
            "season": 1,
            "episode": 2,
            "hash": "[DEADBEEF]",  # Only hash field present
            "confidence": 0.95,
            "reasoning": "High confidence parsing"
        }
        
        process_sftp_diffs(
            sftp_service=mock_sftp_service,
            db_service=mock_db_service,
            diffs=[sample_file_diff],
            remote_base="/remote",
            local_base=str(tmp_path),
            dry_run=False,
            llm_service=mock_llm_service,
            parse_filenames=True,
            use_llm=True,
            llm_confidence_threshold=0.7,
        )
        
        # Verify that hash field was used as fallback
        assert mock_db_service.upsert_downloaded_file.call_count == 1
        upsert_arg = mock_db_service.upsert_downloaded_file.call_args[0][0]
        assert upsert_arg.file_provided_hash_value == "DEADBEEF"  # From hash field

    def test_crc32_field_normalization(self, tmp_path, mock_sftp_service, mock_db_service, mock_llm_service, mocker, sample_file_diff):
        """Test that CRC32 values are properly normalized regardless of source field."""
        # Setup mocks
        mock_executor, mock_future = self.setup_mocks(mocker, tmp_path)
        
        test_cases = [
            # (input_value, expected_normalized)
            ("[a1b2c3d4]", "A1B2C3D4"),  # Lowercase with brackets
            ("A1B2C3D4", "A1B2C3D4"),    # Already normalized
            (" [DeAdBeEf] ", "DEADBEEF"), # Mixed case with spaces and brackets
            ("12345678", "12345678"),     # Numbers only
        ]
        
        for input_value, expected_normalized in test_cases:
            # Reset mocks
            mock_db_service.reset_mock()
            
            # Mock LLM to return test value in crc32 field
            mock_llm_service.parse_filename.return_value = {
                "show_name": "Test Show",
                "season": 1,
                "episode": 2,
                "crc32": input_value,
                "confidence": 0.95,
                "reasoning": "High confidence parsing"
            }
            
            process_sftp_diffs(
                sftp_service=mock_sftp_service,
                db_service=mock_db_service,
                diffs=[sample_file_diff],
                remote_base="/remote",
                local_base=str(tmp_path),
                dry_run=False,
                llm_service=mock_llm_service,
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
            
            # Verify normalization
            assert mock_db_service.upsert_downloaded_file.call_count == 1
            upsert_arg = mock_db_service.upsert_downloaded_file.call_args[0][0]
            assert upsert_arg.file_provided_hash_value == expected_normalized, f"Failed for input: {input_value}"

    def test_hash_field_normalization_fallback(self, tmp_path, mock_sftp_service, mock_db_service, mock_llm_service, mocker, sample_file_diff):
        """Test that hash field values are properly normalized when used as fallback."""
        # Setup mocks
        mock_executor, mock_future = self.setup_mocks(mocker, tmp_path)
        
        # Mock LLM to return only hash field with various formats
        # Note: CRC32 must be exactly 8 hex characters to be valid
        test_cases = [
            ("[deadbeef]", "DEADBEEF"),
            ("  A1B2C3D4  ", "A1B2C3D4"),
            ("[12345678]", "12345678"),  # Fixed: use valid 8-char hex
        ]
        
        for input_value, expected_normalized in test_cases:
            # Reset mocks
            mock_db_service.reset_mock()
            
            mock_llm_service.parse_filename.return_value = {
                "show_name": "Test Show",
                "season": 1,
                "episode": 2,
                "hash": input_value,  # Only hash field present
                "confidence": 0.95,
                "reasoning": "High confidence parsing"
            }
            
            process_sftp_diffs(
                sftp_service=mock_sftp_service,
                db_service=mock_db_service,
                diffs=[sample_file_diff],
                remote_base="/remote",
                local_base=str(tmp_path),
                dry_run=False,
                llm_service=mock_llm_service,
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
            
            # Verify normalization
            assert mock_db_service.upsert_downloaded_file.call_count == 1
            upsert_arg = mock_db_service.upsert_downloaded_file.call_args[0][0]
            assert upsert_arg.file_provided_hash_value == expected_normalized, f"Failed for input: {input_value}"

    def test_invalid_crc32_values_ignored(self, tmp_path, mock_sftp_service, mock_db_service, mock_llm_service, mocker, sample_file_diff):
        """Test that invalid CRC32 values are ignored and not stored."""
        # Setup mocks
        mock_executor, mock_future = self.setup_mocks(mocker, tmp_path)
        
        invalid_values = [
            "TOOLONG123",     # Too long
            "SHORT",          # Too short
            "[INVALID!]",     # Invalid characters
            "",               # Empty string
            None,             # None value
            123,              # Wrong type
        ]
        
        for invalid_value in invalid_values:
            # Reset mocks
            mock_db_service.reset_mock()
            
            mock_llm_service.parse_filename.return_value = {
                "show_name": "Test Show",
                "season": 1,
                "episode": 2,
                "crc32": invalid_value,
                "confidence": 0.95,
                "reasoning": "High confidence parsing"
            }
            
            process_sftp_diffs(
                sftp_service=mock_sftp_service,
                db_service=mock_db_service,
                diffs=[sample_file_diff],
                remote_base="/remote",
                local_base=str(tmp_path),
                dry_run=False,
                llm_service=mock_llm_service,
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
            
            # Verify invalid value was ignored
            assert mock_db_service.upsert_downloaded_file.call_count == 1
            upsert_arg = mock_db_service.upsert_downloaded_file.call_args[0][0]
            assert upsert_arg.file_provided_hash_value is None, f"Invalid value should be ignored: {invalid_value}"

    def test_legacy_hash_field_logging(self, tmp_path, mock_sftp_service, mock_db_service, mock_llm_service, mocker, sample_file_diff, caplog):
        """Test that using legacy hash field generates appropriate log messages."""
        # Setup mocks
        mock_executor, mock_future = self.setup_mocks(mocker, tmp_path)
        
        # Mock LLM to return only hash field (legacy format)
        mock_llm_service.parse_filename.return_value = {
            "show_name": "Test Show",
            "season": 1,
            "episode": 2,
            "hash": "[DEADBEEF]",  # Only hash field present
            "confidence": 0.95,
            "reasoning": "High confidence parsing"
        }
        
        with caplog.at_level("DEBUG"):
            process_sftp_diffs(
                sftp_service=mock_sftp_service,
                db_service=mock_db_service,
                diffs=[sample_file_diff],
                remote_base="/remote",
                local_base=str(tmp_path),
                dry_run=False,
                llm_service=mock_llm_service,
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
        
        # Verify debug log message about legacy field usage
        assert any("Using legacy 'hash' field" in record.message for record in caplog.records)
        assert any("consider updating to 'crc32'" in record.message for record in caplog.records)

    def test_multiple_files_mixed_field_types(self, tmp_path, mock_sftp_service, mock_db_service, mock_llm_service, mocker):
        """Test processing multiple files with mixed field types (crc32 and hash)."""
        # Setup mocks
        mock_executor, mock_future = self.setup_mocks(mocker, tmp_path)
        
        # Create multiple file diffs
        diffs = [
            {
                "name": "File1.S01E01.mkv",
                "path": "/remote/File1.S01E01.mkv",
                "size": 100,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
            },
            {
                "name": "File2.S01E02.mkv",
                "path": "/remote/File2.S01E02.mkv",
                "size": 200,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
            },
            {
                "name": "File3.S01E03.mkv",
                "path": "/remote/File3.S01E03.mkv",
                "size": 300,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
            }
        ]
        
        # Mock multiple futures for concurrent processing
        mock_futures = [mocker.Mock(), mocker.Mock(), mocker.Mock()]
        mock_executor.submit.side_effect = mock_futures
        mocker.patch('utils.sftp_orchestrator.as_completed', return_value=mock_futures)
        for future in mock_futures:
            future.result.return_value = None
        
        # Mock LLM to return different field types for different files
        parse_results = [
            {  # File 1: crc32 field only
                "show_name": "Test Show",
                "season": 1,
                "episode": 1,
                "crc32": "[A1B2C3D4]",
                "confidence": 0.95,
                "reasoning": "High confidence"
            },
            {  # File 2: hash field only (legacy)
                "show_name": "Test Show",
                "season": 1,
                "episode": 2,
                "hash": "[DEADBEEF]",
                "confidence": 0.95,
                "reasoning": "High confidence"
            },
            {  # File 3: both fields (crc32 should take priority)
                "show_name": "Test Show",
                "season": 1,
                "episode": 3,
                "crc32": "[12345678]",
                "hash": "[87654321]",
                "confidence": 0.95,
                "reasoning": "High confidence"
            }
        ]
        
        mock_llm_service.parse_filename.side_effect = parse_results
        
        process_sftp_diffs(
            sftp_service=mock_sftp_service,
            db_service=mock_db_service,
            diffs=diffs,
            remote_base="/remote",
            local_base=str(tmp_path),
            dry_run=False,
            llm_service=mock_llm_service,
            parse_filenames=True,
            use_llm=True,
            llm_confidence_threshold=0.7,
        )
        
        # Verify all files were processed
        assert mock_db_service.upsert_downloaded_file.call_count == 3
        
        # Check each file's hash value
        calls = mock_db_service.upsert_downloaded_file.call_args_list
        
        # File 1: crc32 field
        assert calls[0][0][0].file_provided_hash_value == "A1B2C3D4"
        
        # File 2: hash field (legacy)
        assert calls[1][0][0].file_provided_hash_value == "DEADBEEF"
        
        # File 3: crc32 takes priority over hash
        assert calls[2][0][0].file_provided_hash_value == "12345678"

    def test_database_storage_consistency(self, tmp_path, mock_sftp_service, mock_db_service, mock_llm_service, mocker, sample_file_diff):
        """Test that CRC32 values are consistently stored in database regardless of source field."""
        # Setup mocks
        mock_executor, mock_future = self.setup_mocks(mocker, tmp_path)
        
        # Test both crc32 and hash field sources
        test_cases = [
            {"crc32": "[A1B2C3D4]", "expected": "A1B2C3D4"},
            {"hash": "[DEADBEEF]", "expected": "DEADBEEF"},
        ]
        
        for case in test_cases:
            # Reset mocks
            mock_db_service.reset_mock()
            
            # Create parse result with the test case field
            parse_result = {
                "show_name": "Test Show",
                "season": 1,
                "episode": 2,
                "confidence": 0.95,
                "reasoning": "High confidence parsing"
            }
            parse_result.update(case)
            mock_llm_service.parse_filename.return_value = parse_result
            
            process_sftp_diffs(
                sftp_service=mock_sftp_service,
                db_service=mock_db_service,
                diffs=[sample_file_diff],
                remote_base="/remote",
                local_base=str(tmp_path),
                dry_run=False,
                llm_service=mock_llm_service,
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
            
            # Verify database storage
            assert mock_db_service.upsert_downloaded_file.call_count == 1
            upsert_arg = mock_db_service.upsert_downloaded_file.call_args[0][0]
            
            # Check that the value is stored in the correct database field
            assert hasattr(upsert_arg, 'file_provided_hash_value')
            assert upsert_arg.file_provided_hash_value == case["expected"]
            
            # Verify other fields are also populated correctly
            assert upsert_arg.show_name == "Test Show"
            assert upsert_arg.season == 1
            assert upsert_arg.episode == 2

    def test_no_hash_fields_present(self, tmp_path, mock_sftp_service, mock_db_service, mock_llm_service, mocker, sample_file_diff):
        """Test behavior when neither crc32 nor hash fields are present."""
        # Setup mocks
        mock_executor, mock_future = self.setup_mocks(mocker, tmp_path)
        
        # Mock LLM to return no hash-related fields
        mock_llm_service.parse_filename.return_value = {
            "show_name": "Test Show",
            "season": 1,
            "episode": 2,
            "confidence": 0.95,
            "reasoning": "High confidence parsing"
            # No crc32 or hash fields
        }
        
        process_sftp_diffs(
            sftp_service=mock_sftp_service,
            db_service=mock_db_service,
            diffs=[sample_file_diff],
            remote_base="/remote",
            local_base=str(tmp_path),
            dry_run=False,
            llm_service=mock_llm_service,
            parse_filenames=True,
            use_llm=True,
            llm_confidence_threshold=0.7,
        )
        
        # Verify that file is still processed but without hash value
        assert mock_db_service.upsert_downloaded_file.call_count == 1
        upsert_arg = mock_db_service.upsert_downloaded_file.call_args[0][0]
        assert upsert_arg.file_provided_hash_value is None
        assert upsert_arg.show_name == "Test Show"
        assert upsert_arg.season == 1
        assert upsert_arg.episode == 2

    def test_regex_fallback_field_handling(self, tmp_path, mock_sftp_service, mock_db_service, mock_llm_service, mocker):
        """Test that regex fallback handles field migration correctly (no CRC32 extraction expected)."""
        # Setup mocks
        mock_executor, mock_future = self.setup_mocks(mocker, tmp_path)
        
        # Create a file with CRC32 in filename
        sample_file = {
            "name": "Test.Show.S01E02.[A1B2C3D4].mkv",
            "path": "/remote/Test.Show.S01E02.[A1B2C3D4].mkv",
            "size": 100,
            "modified_time": "2024-01-01T12:00:00",
            "fetched_at": "2024-01-01T12:00:00",
            "is_dir": False,
        }
        
        # Mock LLM to return low confidence (triggers regex fallback)
        mock_llm_service.parse_filename.return_value = {
            "show_name": "Wrong Show",
            "season": 99,
            "episode": 99,
            "confidence": 0.1,  # Low confidence
            "reasoning": "Low confidence parsing"
        }
        
        process_sftp_diffs(
            sftp_service=mock_sftp_service,
            db_service=mock_db_service,
            diffs=[sample_file],
            remote_base="/remote",
            local_base=str(tmp_path),
            dry_run=False,
            llm_service=mock_llm_service,
            parse_filenames=True,
            use_llm=True,
            llm_confidence_threshold=0.7,  # Higher than LLM confidence
        )
        
        # Verify regex fallback extracted season/episode correctly
        assert mock_db_service.upsert_downloaded_file.call_count == 1
        upsert_arg = mock_db_service.upsert_downloaded_file.call_args[0][0]
        
        # Regex should extract season/episode correctly
        assert upsert_arg.season == 1
        assert upsert_arg.episode == 2
        
        # Note: Regex fallback doesn't extract CRC32 - only LLM does
        # So file_provided_hash_value should be None when using regex fallback
        assert upsert_arg.file_provided_hash_value is None