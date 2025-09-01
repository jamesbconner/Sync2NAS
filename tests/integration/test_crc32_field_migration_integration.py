"""
Integration tests for CRC32 field migration.

This module tests the end-to-end field migration behavior across different
components of the system, ensuring that the migration from "hash" to "crc32"
field works correctly in real-world scenarios.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from pathlib import Path

from utils.sftp_orchestrator import process_sftp_diffs
from models.downloaded_file import DownloadedFile


class TestCRC32FieldMigrationIntegration:
    """Integration test suite for CRC32 field migration."""

    @pytest.fixture
    def mock_services(self, mocker):
        """Set up mock services for integration testing."""
        mock_sftp = mocker.Mock()
        mock_db = mocker.Mock()
        mock_llm = mocker.Mock()
        
        # Mock ThreadPoolExecutor for file processing
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
        
        # Mock file filters
        mocker.patch('utils.sftp_orchestrator.is_valid_media_file', return_value=True)
        
        return {
            'sftp': mock_sftp,
            'db': mock_db,
            'llm': mock_llm,
            'executor': mock_executor,
            'future': mock_future
        }

    def test_end_to_end_crc32_field_migration(self, tmp_path, mock_services):
        """Test complete end-to-end field migration workflow."""
        # Create test files with different field configurations
        test_files = [
            {
                "name": "Modern.Show.S01E01.[A1B2C3D4].mkv",
                "path": "/remote/Modern.Show.S01E01.[A1B2C3D4].mkv",
                "size": 100,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
                "llm_result": {
                    "show_name": "Modern Show",
                    "season": 1,
                    "episode": 1,
                    "crc32": "[A1B2C3D4]",  # New field format
                    "confidence": 0.95,
                    "reasoning": "High confidence parsing"
                }
            },
            {
                "name": "Legacy.Show.S01E02.[DEADBEEF].mkv",
                "path": "/remote/Legacy.Show.S01E02.[DEADBEEF].mkv",
                "size": 200,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
                "llm_result": {
                    "show_name": "Legacy Show",
                    "season": 1,
                    "episode": 2,
                    "hash": "[DEADBEEF]",  # Legacy field format
                    "confidence": 0.95,
                    "reasoning": "High confidence parsing"
                }
            },
            {
                "name": "Mixed.Show.S01E03.[12345678].mkv",
                "path": "/remote/Mixed.Show.S01E03.[12345678].mkv",
                "size": 300,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
                "llm_result": {
                    "show_name": "Mixed Show",
                    "season": 1,
                    "episode": 3,
                    "crc32": "[12345678]",  # New field should take priority
                    "hash": "[87654321]",   # Legacy field should be ignored
                    "confidence": 0.95,
                    "reasoning": "High confidence parsing"
                }
            }
        ]
        
        # Set up multiple futures for concurrent processing
        mock_futures = [Mock(), Mock(), Mock()]
        mock_services['executor'].submit.side_effect = mock_futures
        with patch('utils.sftp_orchestrator.as_completed', return_value=mock_futures):
            for future in mock_futures:
                future.result.return_value = None
            
            # Set up LLM responses
            mock_services['llm'].parse_filename.side_effect = [
                file_data["llm_result"] for file_data in test_files
            ]
            
            # Extract just the file diffs
            diffs = [{k: v for k, v in file_data.items() if k != "llm_result"} for file_data in test_files]
            
            # Process the files
            process_sftp_diffs(
                sftp_service=mock_services['sftp'],
                db_service=mock_services['db'],
                diffs=diffs,
                remote_base="/remote",
                local_base=str(tmp_path),
                dry_run=False,
                llm_service=mock_services['llm'],
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
        
        # Verify all files were processed
        assert mock_services['db'].upsert_downloaded_file.call_count == 3
        
        # Check each file's processing results
        calls = mock_services['db'].upsert_downloaded_file.call_args_list
        
        # File 1: Modern format with crc32 field
        file1 = calls[0][0][0]
        assert file1.show_name == "Modern Show"
        assert file1.season == 1
        assert file1.episode == 1
        assert file1.file_provided_hash_value == "A1B2C3D4"
        
        # File 2: Legacy format with hash field
        file2 = calls[1][0][0]
        assert file2.show_name == "Legacy Show"
        assert file2.season == 1
        assert file2.episode == 2
        assert file2.file_provided_hash_value == "DEADBEEF"
        
        # File 3: Mixed format - crc32 should take priority
        file3 = calls[2][0][0]
        assert file3.show_name == "Mixed Show"
        assert file3.season == 1
        assert file3.episode == 3
        assert file3.file_provided_hash_value == "12345678"  # From crc32, not hash

    def test_backward_compatibility_during_transition(self, tmp_path, mock_services):
        """Test that the system handles mixed field types during transition period."""
        # Simulate a scenario where some LLM responses use old format, some use new
        transition_files = [
            {
                "name": "Old.Format.S01E01.mkv",
                "path": "/remote/Old.Format.S01E01.mkv",
                "size": 100,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
            },
            {
                "name": "New.Format.S01E02.mkv",
                "path": "/remote/New.Format.S01E02.mkv",
                "size": 200,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
            }
        ]
        
        # Set up multiple futures
        mock_futures = [Mock(), Mock()]
        mock_services['executor'].submit.side_effect = mock_futures
        with patch('utils.sftp_orchestrator.as_completed', return_value=mock_futures):
            for future in mock_futures:
                future.result.return_value = None
            
            # Mock LLM responses with different field formats
            mock_services['llm'].parse_filename.side_effect = [
                {  # Old format response
                    "show_name": "Old Format Show",
                    "season": 1,
                    "episode": 1,
                    "hash": "[DEADBEEF]",  # Legacy field only (valid 8-char hex)
                    "confidence": 0.95,
                    "reasoning": "Legacy LLM response"
                },
                {  # New format response
                    "show_name": "New Format Show",
                    "season": 1,
                    "episode": 2,
                    "crc32": "[A1B2C3D4]",  # Modern field only (valid 8-char hex)
                    "confidence": 0.95,
                    "reasoning": "Modern LLM response"
                }
            ]
            
            process_sftp_diffs(
                sftp_service=mock_services['sftp'],
                db_service=mock_services['db'],
                diffs=transition_files,
                remote_base="/remote",
                local_base=str(tmp_path),
                dry_run=False,
                llm_service=mock_services['llm'],
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
        
        # Verify both files were processed correctly
        assert mock_services['db'].upsert_downloaded_file.call_count == 2
        calls = mock_services['db'].upsert_downloaded_file.call_args_list
        
        # Old format file should use hash field
        old_file = calls[0][0][0]
        assert old_file.file_provided_hash_value == "DEADBEEF"
        
        # New format file should use crc32 field
        new_file = calls[1][0][0]
        assert new_file.file_provided_hash_value == "A1B2C3D4"

    def test_database_consistency_across_field_types(self, tmp_path, mock_services):
        """Test that database storage is consistent regardless of source field type."""
        # Test files with various field configurations
        consistency_files = [
            {
                "name": "Test1.S01E01.mkv",
                "path": "/remote/Test1.S01E01.mkv",
                "size": 100,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
                "expected_hash": "AAAAAAAA",
                "llm_result": {
                    "show_name": "Test Show 1",
                    "season": 1,
                    "episode": 1,
                    "crc32": "[aaaaaaaa]",  # Lowercase, should be normalized
                    "confidence": 0.95,
                    "reasoning": "Test case 1"
                }
            },
            {
                "name": "Test2.S01E02.mkv",
                "path": "/remote/Test2.S01E02.mkv",
                "size": 200,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
                "expected_hash": "BBBBBBBB",
                "llm_result": {
                    "show_name": "Test Show 2",
                    "season": 1,
                    "episode": 2,
                    "hash": "  [bbbbbbbb]  ",  # Legacy field with spaces, should be normalized
                    "confidence": 0.95,
                    "reasoning": "Test case 2"
                }
            },
            {
                "name": "Test3.S01E03.mkv",
                "path": "/remote/Test3.S01E03.mkv",
                "size": 300,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
                "expected_hash": "CCCCCCCC",
                "llm_result": {
                    "show_name": "Test Show 3",
                    "season": 1,
                    "episode": 3,
                    "crc32": "CCCCCCCC",  # Already normalized
                    "hash": "DDDDDDDD",   # Should be ignored in favor of crc32
                    "confidence": 0.95,
                    "reasoning": "Test case 3"
                }
            }
        ]
        
        # Set up multiple futures
        mock_futures = [Mock(), Mock(), Mock()]
        mock_services['executor'].submit.side_effect = mock_futures
        with patch('utils.sftp_orchestrator.as_completed', return_value=mock_futures):
            for future in mock_futures:
                future.result.return_value = None
            
            # Set up LLM responses
            mock_services['llm'].parse_filename.side_effect = [
                file_data["llm_result"] for file_data in consistency_files
            ]
            
            # Extract file diffs
            diffs = [{k: v for k, v in file_data.items() if k not in ["llm_result", "expected_hash"]} 
                    for file_data in consistency_files]
            
            process_sftp_diffs(
                sftp_service=mock_services['sftp'],
                db_service=mock_services['db'],
                diffs=diffs,
                remote_base="/remote",
                local_base=str(tmp_path),
                dry_run=False,
                llm_service=mock_services['llm'],
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
        
        # Verify all files were processed
        assert mock_services['db'].upsert_downloaded_file.call_count == 3
        calls = mock_services['db'].upsert_downloaded_file.call_args_list
        
        # Check that all hash values were normalized correctly and stored consistently
        for i, file_data in enumerate(consistency_files):
            stored_file = calls[i][0][0]
            expected_hash = file_data["expected_hash"]
            
            # Verify the hash value is stored correctly in the database field
            assert stored_file.file_provided_hash_value == expected_hash, \
                f"File {i+1}: Expected {expected_hash}, got {stored_file.file_provided_hash_value}"
            
            # Verify other fields are also stored correctly
            assert stored_file.show_name == file_data["llm_result"]["show_name"]
            assert stored_file.season == file_data["llm_result"]["season"]
            assert stored_file.episode == file_data["llm_result"]["episode"]

    def test_error_handling_during_field_migration(self, tmp_path, mock_services):
        """Test error handling when field migration encounters issues."""
        error_test_files = [
            {
                "name": "Valid.File.S01E01.mkv",
                "path": "/remote/Valid.File.S01E01.mkv",
                "size": 100,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
            },
            {
                "name": "Problem.File.S01E02.mkv",
                "path": "/remote/Problem.File.S01E02.mkv",
                "size": 200,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
            }
        ]
        
        # Set up multiple futures
        mock_futures = [Mock(), Mock()]
        mock_services['executor'].submit.side_effect = mock_futures
        with patch('utils.sftp_orchestrator.as_completed', return_value=mock_futures):
            for future in mock_futures:
                future.result.return_value = None
            
            # Mock LLM responses - one valid, one with invalid hash
            mock_services['llm'].parse_filename.side_effect = [
                {  # Valid response
                    "show_name": "Valid Show",
                    "season": 1,
                    "episode": 1,
                    "crc32": "[A1B2C3D4]",
                    "confidence": 0.95,
                    "reasoning": "Valid parsing"
                },
                {  # Response with invalid hash format
                    "show_name": "Problem Show",
                    "season": 1,
                    "episode": 2,
                    "crc32": "INVALID_HASH_FORMAT",  # Invalid format
                    "confidence": 0.95,
                    "reasoning": "Invalid hash format"
                }
            ]
            
            # This should not raise an exception
            process_sftp_diffs(
                sftp_service=mock_services['sftp'],
                db_service=mock_services['db'],
                diffs=error_test_files,
                remote_base="/remote",
                local_base=str(tmp_path),
                dry_run=False,
                llm_service=mock_services['llm'],
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
        
        # Verify both files were processed despite the invalid hash
        assert mock_services['db'].upsert_downloaded_file.call_count == 2
        calls = mock_services['db'].upsert_downloaded_file.call_args_list
        
        # Valid file should have hash stored
        valid_file = calls[0][0][0]
        assert valid_file.file_provided_hash_value == "A1B2C3D4"
        
        # Problem file should have None for hash (invalid format rejected)
        problem_file = calls[1][0][0]
        assert problem_file.file_provided_hash_value is None
        assert problem_file.show_name == "Problem Show"  # Other fields should still be processed

    def test_performance_with_large_batch_mixed_fields(self, tmp_path, mock_services):
        """Test performance and correctness with a large batch of mixed field types."""
        # Create a large batch of files with mixed field configurations
        batch_size = 50
        test_files = []
        expected_results = []
        
        for i in range(batch_size):
            file_data = {
                "name": f"Batch.File.{i:03d}.S01E{i+1:02d}.mkv",
                "path": f"/remote/Batch.File.{i:03d}.S01E{i+1:02d}.mkv",
                "size": 100 + i,
                "modified_time": "2024-01-01T12:00:00",
                "fetched_at": "2024-01-01T12:00:00",
                "is_dir": False,
            }
            
            # Alternate between different field configurations
            if i % 3 == 0:
                # crc32 field only
                llm_result = {
                    "show_name": f"Batch Show {i}",
                    "season": 1,
                    "episode": i + 1,
                    "crc32": f"[{i:08X}]",
                    "confidence": 0.95,
                    "reasoning": f"crc32 field test {i}"
                }
                expected_hash = f"{i:08X}"
            elif i % 3 == 1:
                # hash field only (legacy)
                llm_result = {
                    "show_name": f"Batch Show {i}",
                    "season": 1,
                    "episode": i + 1,
                    "hash": f"[{i:08X}]",
                    "confidence": 0.95,
                    "reasoning": f"hash field test {i}"
                }
                expected_hash = f"{i:08X}"
            else:
                # both fields (crc32 should take priority)
                llm_result = {
                    "show_name": f"Batch Show {i}",
                    "season": 1,
                    "episode": i + 1,
                    "crc32": f"[{i:08X}]",
                    "hash": f"[{(i+1000):08X}]",  # Different value that should be ignored
                    "confidence": 0.95,
                    "reasoning": f"both fields test {i}"
                }
                expected_hash = f"{i:08X}"  # Should use crc32 value
            
            test_files.append(file_data)
            expected_results.append({
                "llm_result": llm_result,
                "expected_hash": expected_hash
            })
        
        # Set up multiple futures for concurrent processing
        mock_futures = [Mock() for _ in range(batch_size)]
        mock_services['executor'].submit.side_effect = mock_futures
        with patch('utils.sftp_orchestrator.as_completed', return_value=mock_futures):
            for future in mock_futures:
                future.result.return_value = None
            
            # Set up LLM responses
            mock_services['llm'].parse_filename.side_effect = [
                result["llm_result"] for result in expected_results
            ]
            
            process_sftp_diffs(
                sftp_service=mock_services['sftp'],
                db_service=mock_services['db'],
                diffs=test_files,
                remote_base="/remote",
                local_base=str(tmp_path),
                dry_run=False,
                llm_service=mock_services['llm'],
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
        
        # Verify all files were processed
        assert mock_services['db'].upsert_downloaded_file.call_count == batch_size
        calls = mock_services['db'].upsert_downloaded_file.call_args_list
        
        # Verify each file was processed correctly
        for i, expected in enumerate(expected_results):
            stored_file = calls[i][0][0]
            expected_hash = expected["expected_hash"]
            
            assert stored_file.file_provided_hash_value == expected_hash, \
                f"File {i}: Expected {expected_hash}, got {stored_file.file_provided_hash_value}"
            assert stored_file.show_name == f"Batch Show {i}"
            assert stored_file.season == 1
            assert stored_file.episode == i + 1