"""
End-to-end validation tests for CRC32 field migration.

This module provides comprehensive validation of the complete SFTP download and parsing
workflow with the new CRC32 field names, ensuring that:
1. CRC32 values are correctly extracted from filenames
2. CRC32 values are properly normalized and stored in the database
3. Database queries and updates work with the new field structure
4. The complete workflow functions correctly with mixed field types

Requirements covered: 4.2, 4.3
"""

import pytest
import tempfile
import os
import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from utils.sftp_orchestrator import process_sftp_diffs, download_from_remote
from models.downloaded_file import DownloadedFile
from services.hashing_service import HashingService
from utils.filename_parser import parse_filename


class TestEndToEndCRC32Validation:
    """End-to-end validation test suite for CRC32 field migration."""

    @pytest.fixture
    def temp_directory(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_services(self, mocker):
        """Set up comprehensive mock services for end-to-end testing."""
        # Mock SFTP service
        mock_sftp = mocker.Mock()
        mock_sftp.host = "test.example.com"
        mock_sftp.port = 22
        mock_sftp.username = "testuser"
        mock_sftp.ssh_key_path = "/path/to/key"
        mock_sftp.llm_service = None
        
        # Mock database service
        mock_db = mocker.Mock()
        mock_db.get_sftp_diffs.return_value = []
        mock_db.clear_sftp_temp_files.return_value = None
        mock_db.insert_sftp_temp_files.return_value = None
        mock_db.add_downloaded_file.return_value = None
        mock_db.upsert_downloaded_file.return_value = None
        
        # Mock LLM service
        mock_llm = mocker.Mock()
        
        # Mock hashing service
        mock_hashing = mocker.Mock()
        mock_hashing.calculate_crc32.return_value = "COMPUTED1"
        
        # Mock ThreadPoolExecutor for concurrent processing
        mock_executor = mocker.Mock()
        mock_future = mocker.Mock()
        mock_executor.__enter__ = mocker.Mock(return_value=mock_executor)
        mock_executor.submit.return_value = mock_future
        mock_executor.__exit__ = mocker.Mock(return_value=None)
        mocker.patch('utils.sftp_orchestrator.ThreadPoolExecutor', return_value=mock_executor)
        mocker.patch('utils.sftp_orchestrator.as_completed', return_value=[mock_future])
        mock_future.result.return_value = None
        
        # Mock SFTPService constructor for download tasks
        mock_new_sftp = mocker.Mock()
        mock_new_sftp.__enter__ = mocker.Mock(return_value=mock_new_sftp)
        mock_new_sftp.__exit__ = mocker.Mock(return_value=None)
        mock_new_sftp.download_file.return_value = None
        mocker.patch('services.sftp_service.SFTPService', return_value=mock_new_sftp)
        
        # Mock file filters to allow all test files
        mocker.patch('utils.sftp_orchestrator.is_valid_media_file', return_value=True)
        mocker.patch('utils.sftp_orchestrator.is_valid_directory', return_value=True)
        
        return {
            'sftp': mock_sftp,
            'db': mock_db,
            'llm': mock_llm,
            'hashing': mock_hashing,
            'executor': mock_executor,
            'future': mock_future
        }

    def test_complete_sftp_workflow_with_crc32_extraction(self, temp_directory, mock_services):
        """
        Test the complete SFTP download and parsing workflow with CRC32 extraction.
        
        This test validates:
        - Files are downloaded via SFTP
        - Filenames are parsed to extract CRC32 values
        - CRC32 values are normalized and stored correctly
        - Database operations work with the new field structure
        """
        # Create test files with various CRC32 formats
        test_files = [
            {
                "name": "[SubsPlease] Modern Anime - 01 [A1B2C3D4].mkv",
                "path": "/remote/modern/[SubsPlease] Modern Anime - 01 [A1B2C3D4].mkv",
                "remote_path": "/remote/modern/[SubsPlease] Modern Anime - 01 [A1B2C3D4].mkv",
                "size": 1024000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
                "expected_crc32": "A1B2C3D4",
                "llm_response": {
                    "show_name": "Modern Anime",
                    "season": None,
                    "episode": 1,
                    "crc32": "A1B2C3D4",  # New field format
                    "confidence": 0.95,
                    "reasoning": "Clear CRC32 extraction from filename"
                }
            },
            {
                "name": "Legacy Show S01E02 [deadbeef].mkv",
                "path": "/remote/legacy/Legacy Show S01E02 [deadbeef].mkv",
                "remote_path": "/remote/legacy/Legacy Show S01E02 [deadbeef].mkv",
                "size": 2048000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
                "expected_crc32": "DEADBEEF",  # Should be normalized to uppercase
                "llm_response": {
                    "show_name": "Legacy Show",
                    "season": 1,
                    "episode": 2,
                    "hash": "deadbeef",  # Legacy field format (lowercase)
                    "confidence": 0.90,
                    "reasoning": "Legacy hash field extraction"
                }
            },
            {
                "name": "Mixed Format Show - 03 [12345678].mkv",
                "path": "/remote/mixed/Mixed Format Show - 03 [12345678].mkv",
                "remote_path": "/remote/mixed/Mixed Format Show - 03 [12345678].mkv",
                "size": 1536000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
                "expected_crc32": "12345678",
                "llm_response": {
                    "show_name": "Mixed Format Show",
                    "season": None,
                    "episode": 3,
                    "crc32": "12345678",  # New field should take priority
                    "hash": "87654321",   # Legacy field should be ignored
                    "confidence": 0.95,
                    "reasoning": "Both fields present, crc32 takes priority"
                }
            }
        ]
        
        # Create actual test files in temp directory
        for file_data in test_files:
            file_path = Path(temp_directory) / file_data["name"]
            file_path.write_text("test content")
        
        # Set up multiple futures for concurrent processing
        mock_futures = [Mock() for _ in test_files]
        mock_services['executor'].submit.side_effect = mock_futures
        
        with patch('utils.sftp_orchestrator.as_completed', return_value=mock_futures):
            for future in mock_futures:
                future.result.return_value = None
            
            # Set up LLM responses
            mock_services['llm'].parse_filename.side_effect = [
                file_data["llm_response"] for file_data in test_files
            ]
            
            # Extract file diffs for processing
            diffs = [{k: v for k, v in file_data.items() 
                     if k not in ["expected_crc32", "llm_response"]} 
                    for file_data in test_files]
            
            # Process the complete SFTP workflow
            process_sftp_diffs(
                sftp_service=mock_services['sftp'],
                db_service=mock_services['db'],
                diffs=diffs,
                remote_base="/remote",
                local_base=temp_directory,
                dry_run=False,
                llm_service=mock_services['llm'],
                hashing_service=mock_services['hashing'],
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
        
        # Verify all files were processed through the complete workflow
        assert mock_services['db'].add_downloaded_file.call_count == len(test_files)
        assert mock_services['db'].upsert_downloaded_file.call_count == len(test_files)
        
        # Verify each file was processed correctly
        upsert_calls = mock_services['db'].upsert_downloaded_file.call_args_list
        
        for i, file_data in enumerate(test_files):
            stored_file = upsert_calls[i][0][0]
            expected_crc32 = file_data["expected_crc32"]
            
            # Verify CRC32 extraction and normalization
            assert stored_file.file_provided_hash_value == expected_crc32, \
                f"File {i+1}: Expected CRC32 {expected_crc32}, got {stored_file.file_provided_hash_value}"
            
            # Verify other parsed metadata
            assert stored_file.show_name == file_data["llm_response"]["show_name"]
            assert stored_file.season == file_data["llm_response"]["season"]
            assert stored_file.episode == file_data["llm_response"]["episode"]
            assert stored_file.confidence == file_data["llm_response"]["confidence"]
            
            # Verify file metadata
            assert stored_file.name == file_data["name"]
            assert stored_file.remote_path == file_data["remote_path"]
            assert stored_file.size == file_data["size"]

    def test_database_queries_with_new_field_structure(self, temp_directory, mock_services):
        """
        Test that database queries and updates work correctly with the new field structure.
        
        This test validates:
        - Database upsert operations handle the new field structure
        - CRC32 values are stored in the correct database field
        - Database queries can retrieve files by CRC32 values
        """
        # Test file with CRC32 data
        test_file = {
            "name": "Database Test Show S01E01 [ABCDEF12].mkv",
            "path": "/remote/db_test/Database Test Show S01E01 [ABCDEF12].mkv",
            "remote_path": "/remote/db_test/Database Test Show S01E01 [ABCDEF12].mkv",
            "size": 1024000,
            "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
            "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
            "is_dir": False,
        }
        
        # Create test file
        file_path = Path(temp_directory) / test_file["name"]
        file_path.write_text("database test content")
        
        # Set up single future
        mock_future = Mock()
        mock_services['executor'].submit.return_value = mock_future
        
        with patch('utils.sftp_orchestrator.as_completed', return_value=[mock_future]):
            mock_future.result.return_value = None
            
            # Set up LLM response
            mock_services['llm'].parse_filename.return_value = {
                "show_name": "Database Test Show",
                "season": 1,
                "episode": 1,
                "crc32": "ABCDEF12",
                "confidence": 0.95,
                "reasoning": "Database field structure test"
            }
            
            # Process the file
            process_sftp_diffs(
                sftp_service=mock_services['sftp'],
                db_service=mock_services['db'],
                diffs=[test_file],
                remote_base="/remote",
                local_base=temp_directory,
                dry_run=False,
                llm_service=mock_services['llm'],
                hashing_service=mock_services['hashing'],
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
        
        # Verify database operations
        assert mock_services['db'].upsert_downloaded_file.call_count == 1
        
        # Get the stored file object
        stored_file = mock_services['db'].upsert_downloaded_file.call_args_list[0][0][0]
        
        # Verify the file object has the correct structure for database storage
        assert isinstance(stored_file, DownloadedFile)
        assert stored_file.file_provided_hash_value == "ABCDEF12"
        assert stored_file.show_name == "Database Test Show"
        assert stored_file.season == 1
        assert stored_file.episode == 1
        
        # Verify the file can be serialized for database storage
        db_tuple = stored_file.to_db_tuple()
        assert isinstance(db_tuple, tuple)
        assert len(db_tuple) == 20  # Expected number of database fields
        
        # Verify the file can be reconstructed from database record
        db_record = {
            "id": 1,
            "name": stored_file.name,
            "remote_path": stored_file.remote_path,
            "current_path": stored_file.current_path,
            "size": stored_file.size,
            "modified_time": stored_file.modified_time,
            "fetched_at": stored_file.fetched_at,
            "is_dir": stored_file.is_dir,
            "status": stored_file.status.value,
            "file_hash": stored_file.file_hash,
            "file_provided_hash_value": stored_file.file_provided_hash_value,
            "show_name": stored_file.show_name,
            "season": stored_file.season,
            "episode": stored_file.episode,
            "confidence": stored_file.confidence,
            "reasoning": stored_file.reasoning,
            "tmdb_id": stored_file.tmdb_id,
            "routing_attempts": stored_file.routing_attempts,
            "last_routing_attempt": stored_file.last_routing_attempt,
            "error_message": stored_file.error_message,
            "metadata": stored_file.metadata
        }
        
        reconstructed_file = DownloadedFile.from_db_record(db_record)
        assert reconstructed_file.file_provided_hash_value == "ABCDEF12"
        assert reconstructed_file.show_name == "Database Test Show"

    def test_crc32_normalization_and_validation(self, temp_directory, mock_services):
        """
        Test CRC32 normalization and validation during the complete workflow.
        
        This test validates:
        - Various CRC32 formats are normalized correctly
        - Invalid CRC32 values are handled gracefully
        - Normalization works consistently across field types
        """
        # Test files with various CRC32 formats
        normalization_test_files = [
            {
                "name": "Lowercase Test [abcdef12].mkv",
                "path": "/remote/norm/Lowercase Test [abcdef12].mkv",
                "remote_path": "/remote/norm/Lowercase Test [abcdef12].mkv",
                "size": 1024000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
                "expected_crc32": "ABCDEF12",
                "llm_response": {
                    "show_name": "Lowercase Test",
                    "season": None,
                    "episode": 1,
                    "crc32": "[abcdef12]",  # Lowercase with brackets
                    "confidence": 0.95,
                    "reasoning": "Lowercase normalization test"
                }
            },
            {
                "name": "Spaces Test [  12345678  ].mkv",
                "path": "/remote/norm/Spaces Test [  12345678  ].mkv",
                "remote_path": "/remote/norm/Spaces Test [  12345678  ].mkv",
                "size": 1024000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
                "expected_crc32": "12345678",
                "llm_response": {
                    "show_name": "Spaces Test",
                    "season": None,
                    "episode": 1,
                    "hash": "  12345678  ",  # Legacy field with spaces
                    "confidence": 0.95,
                    "reasoning": "Spaces normalization test"
                }
            },
            {
                "name": "Invalid Format Test.mkv",
                "path": "/remote/norm/Invalid Format Test.mkv",
                "remote_path": "/remote/norm/Invalid Format Test.mkv",
                "size": 1024000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
                "expected_crc32": None,  # Invalid format should result in None
                "llm_response": {
                    "show_name": "Invalid Format Test",
                    "season": None,
                    "episode": 1,
                    "crc32": "INVALID_FORMAT_TOO_LONG",  # Invalid format
                    "confidence": 0.95,
                    "reasoning": "Invalid format test"
                }
            },
            {
                "name": "No Hash Test.mkv",
                "path": "/remote/norm/No Hash Test.mkv",
                "remote_path": "/remote/norm/No Hash Test.mkv",
                "size": 1024000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
                "expected_crc32": None,
                "llm_response": {
                    "show_name": "No Hash Test",
                    "season": None,
                    "episode": 1,
                    "crc32": None,  # No hash present
                    "confidence": 0.95,
                    "reasoning": "No hash test"
                }
            }
        ]
        
        # Create test files
        for file_data in normalization_test_files:
            file_path = Path(temp_directory) / file_data["name"]
            file_path.write_text("normalization test content")
        
        # Set up multiple futures
        mock_futures = [Mock() for _ in normalization_test_files]
        mock_services['executor'].submit.side_effect = mock_futures
        
        with patch('utils.sftp_orchestrator.as_completed', return_value=mock_futures):
            for future in mock_futures:
                future.result.return_value = None
            
            # Set up LLM responses
            mock_services['llm'].parse_filename.side_effect = [
                file_data["llm_response"] for file_data in normalization_test_files
            ]
            
            # Extract file diffs
            diffs = [{k: v for k, v in file_data.items() 
                     if k not in ["expected_crc32", "llm_response"]} 
                    for file_data in normalization_test_files]
            
            # Process files
            process_sftp_diffs(
                sftp_service=mock_services['sftp'],
                db_service=mock_services['db'],
                diffs=diffs,
                remote_base="/remote",
                local_base=temp_directory,
                dry_run=False,
                llm_service=mock_services['llm'],
                hashing_service=mock_services['hashing'],
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
        
        # Verify all files were processed
        assert mock_services['db'].upsert_downloaded_file.call_count == len(normalization_test_files)
        
        # Verify normalization results
        upsert_calls = mock_services['db'].upsert_downloaded_file.call_args_list
        
        for i, file_data in enumerate(normalization_test_files):
            stored_file = upsert_calls[i][0][0]
            expected_crc32 = file_data["expected_crc32"]
            
            assert stored_file.file_provided_hash_value == expected_crc32, \
                f"File {i+1} ({file_data['name']}): Expected {expected_crc32}, got {stored_file.file_provided_hash_value}"

    def test_complete_download_workflow_integration(self, temp_directory, mock_services):
        """
        Test the complete download_from_remote workflow with CRC32 field migration.
        
        This test validates:
        - The full download_from_remote function works with new field structure
        - Remote file listing, diffing, and downloading work together
        - CRC32 values are preserved through the complete workflow
        """
        # Mock remote file listing
        remote_files = [
            {
                "name": "Complete Workflow Test S01E01 [FEDCBA98].mkv",
                "path": "/remote/complete/Complete Workflow Test S01E01 [FEDCBA98].mkv",
                "size": 2048000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
            }
        ]
        
        # Mock SFTP service methods
        mock_services['sftp'].list_remote_dir.return_value = remote_files
        
        # Mock database diff results
        mock_services['db'].get_sftp_diffs.return_value = [
            {
                **remote_files[0],
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "remote_path": remote_files[0]["path"]
            }
        ]
        
        # Create test file
        file_path = Path(temp_directory) / remote_files[0]["name"]
        file_path.write_text("complete workflow test content")
        
        # Set up future for download
        mock_future = Mock()
        mock_services['executor'].submit.return_value = mock_future
        
        with patch('utils.sftp_orchestrator.as_completed', return_value=[mock_future]):
            mock_future.result.return_value = None
            
            # Mock the parse_filename function where it's imported in sftp_orchestrator
            with patch('utils.sftp_orchestrator.parse_filename') as mock_parse:
                mock_parse.return_value = {
                    "show_name": "Complete Workflow Test",
                    "season": 1,
                    "episode": 1,
                    "crc32": "FEDCBA98",
                    "confidence": 0.95,
                    "reasoning": "Complete workflow integration test"
                }
            
                # Run the complete download workflow
                download_from_remote(
                    sftp=mock_services['sftp'],
                    db=mock_services['db'],
                    remote_paths=["/remote/complete"],
                    incoming_path=temp_directory,
                    dry_run=False,
                    hashing_service=mock_services['hashing'],
                    parse_filenames=True,
                    use_llm=True,
                    llm_confidence_threshold=0.7,
                )
        
        # Verify the complete workflow executed correctly
        mock_services['sftp'].list_remote_dir.assert_called_once_with("/remote/complete")
        mock_services['db'].clear_sftp_temp_files.assert_called_once()
        mock_services['db'].insert_sftp_temp_files.assert_called_once_with(remote_files)
        mock_services['db'].get_sftp_diffs.assert_called_once()
        
        # Verify file was processed with CRC32 extraction
        assert mock_services['db'].upsert_downloaded_file.call_count == 1
        stored_file = mock_services['db'].upsert_downloaded_file.call_args_list[0][0][0]
        
        assert stored_file.file_provided_hash_value == "FEDCBA98"
        assert stored_file.show_name == "Complete Workflow Test"
        assert stored_file.season == 1
        assert stored_file.episode == 1

    def test_error_resilience_in_complete_workflow(self, temp_directory, mock_services):
        """
        Test error resilience during the complete workflow with CRC32 field migration.
        
        This test validates:
        - The workflow continues processing other files when individual files fail
        - CRC32 extraction errors don't break the entire workflow
        - Database operations are resilient to field migration issues
        """
        # Test files with various scenarios including errors
        test_files = [
            {
                "name": "Good File S01E01 [ABCDEF12].mkv",
                "path": "/remote/error/Good File S01E01 [ABCDEF12].mkv",
                "remote_path": "/remote/error/Good File S01E01 [ABCDEF12].mkv",
                "size": 1024000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
                "should_succeed": True,
                "llm_response": {
                    "show_name": "Good File",
                    "season": 1,
                    "episode": 1,
                    "crc32": "ABCDEF12",
                    "confidence": 0.95,
                    "reasoning": "Good file test"
                }
            },
            {
                "name": "LLM Error File S01E02.mkv",
                "path": "/remote/error/LLM Error File S01E02.mkv",
                "remote_path": "/remote/error/LLM Error File S01E02.mkv",
                "size": 1024000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
                "should_succeed": False,
                "llm_response": Exception("LLM parsing failed")
            },
            {
                "name": "Recovery File S01E03 [12345678].mkv",
                "path": "/remote/error/Recovery File S01E03 [12345678].mkv",
                "remote_path": "/remote/error/Recovery File S01E03 [12345678].mkv",
                "size": 1024000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
                "should_succeed": True,
                "llm_response": {
                    "show_name": "Recovery File",
                    "season": 1,
                    "episode": 3,
                    "crc32": "12345678",
                    "confidence": 0.95,
                    "reasoning": "Recovery after error test"
                }
            }
        ]
        
        # Create test files
        for file_data in test_files:
            file_path = Path(temp_directory) / file_data["name"]
            file_path.write_text("error resilience test content")
        
        # Set up multiple futures
        mock_futures = [Mock() for _ in test_files]
        mock_services['executor'].submit.side_effect = mock_futures
        
        with patch('utils.sftp_orchestrator.as_completed', return_value=mock_futures):
            for future in mock_futures:
                future.result.return_value = None
            
            # Set up LLM responses with one failure
            llm_responses = []
            for file_data in test_files:
                if isinstance(file_data["llm_response"], Exception):
                    llm_responses.append(file_data["llm_response"])
                else:
                    llm_responses.append(file_data["llm_response"])
            
            mock_services['llm'].parse_filename.side_effect = llm_responses
            
            # Extract file diffs
            diffs = [{k: v for k, v in file_data.items() 
                     if k not in ["should_succeed", "llm_response"]} 
                    for file_data in test_files]
            
            # Process files - should not raise exception despite LLM error
            process_sftp_diffs(
                sftp_service=mock_services['sftp'],
                db_service=mock_services['db'],
                diffs=diffs,
                remote_base="/remote",
                local_base=temp_directory,
                dry_run=False,
                llm_service=mock_services['llm'],
                hashing_service=mock_services['hashing'],
                parse_filenames=True,
                use_llm=True,
                llm_confidence_threshold=0.7,
            )
        
        # Verify all files were attempted to be processed
        assert mock_services['db'].add_downloaded_file.call_count == len(test_files)
        assert mock_services['db'].upsert_downloaded_file.call_count == len(test_files)
        
        # Verify successful files were processed correctly
        upsert_calls = mock_services['db'].upsert_downloaded_file.call_args_list
        
        successful_files = [f for f in test_files if f["should_succeed"]]
        successful_calls = [call for i, call in enumerate(upsert_calls) 
                          if test_files[i]["should_succeed"]]
        
        for i, file_data in enumerate(successful_files):
            stored_file = successful_calls[i][0][0]
            
            # Verify successful files have correct CRC32 values
            if "crc32" in file_data["llm_response"]:
                assert stored_file.file_provided_hash_value == file_data["llm_response"]["crc32"]
            
            assert stored_file.show_name == file_data["llm_response"]["show_name"]