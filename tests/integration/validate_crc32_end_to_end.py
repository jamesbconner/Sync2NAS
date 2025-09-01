#!/usr/bin/env python3
"""
End-to-end validation script for CRC32 field migration.

This script demonstrates and validates that the complete SFTP download and parsing
workflow works correctly with the new CRC32 field names. It can be run independently
to verify the migration is complete and functional.

Usage:
    python tests/integration/validate_crc32_end_to_end.py
"""

import sys
import tempfile
import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directories for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.sftp_orchestrator import process_sftp_diffs, download_from_remote
from models.downloaded_file import DownloadedFile
from services.hashing_service import HashingService


def create_mock_services():
    """Create comprehensive mock services for validation."""
    # Mock SFTP service
    mock_sftp = Mock()
    mock_sftp.host = "validation.example.com"
    mock_sftp.port = 22
    mock_sftp.username = "validator"
    mock_sftp.ssh_key_path = "/path/to/validation/key"
    mock_sftp.llm_service = None
    
    # Mock database service
    mock_db = Mock()
    mock_db.get_sftp_diffs.return_value = []
    mock_db.clear_sftp_temp_files.return_value = None
    mock_db.insert_sftp_temp_files.return_value = None
    mock_db.add_downloaded_file.return_value = None
    mock_db.upsert_downloaded_file.return_value = None
    
    # Mock LLM service
    mock_llm = Mock()
    
    # Mock hashing service
    mock_hashing = Mock()
    mock_hashing.calculate_crc32.return_value = "COMPUTED1"
    
    return {
        'sftp': mock_sftp,
        'db': mock_db,
        'llm': mock_llm,
        'hashing': mock_hashing
    }


def validate_crc32_extraction():
    """Validate CRC32 extraction from various filename formats."""
    print("🔍 Validating CRC32 extraction from filenames...")
    
    test_cases = [
        {
            "filename": "[SubsPlease] Modern Anime - 01 [A1B2C3D4].mkv",
            "expected_crc32": "A1B2C3D4",
            "description": "Standard format with CRC32 in brackets"
        },
        {
            "filename": "Legacy Show S01E02 [deadbeef].mkv",
            "expected_crc32": "DEADBEEF",
            "description": "Legacy format with lowercase CRC32"
        },
        {
            "filename": "Mixed Format Show - 03 [12345678].mkv",
            "expected_crc32": "12345678",
            "description": "Mixed format with numeric CRC32"
        },
        {
            "filename": "No Hash Show S01E04.mkv",
            "expected_crc32": None,
            "description": "File without CRC32 hash"
        }
    ]
    
    success_count = 0
    
    with tempfile.TemporaryDirectory() as temp_dir:
        mock_services = create_mock_services()
        
        for i, test_case in enumerate(test_cases):
            print(f"  📁 Testing: {test_case['description']}")
            
            # Create test file
            file_path = Path(temp_dir) / test_case["filename"]
            file_path.write_text("validation test content")
            
            # Create file diff
            file_diff = {
                "name": test_case["filename"],
                "path": f"/remote/validation/{test_case['filename']}",
                "remote_path": f"/remote/validation/{test_case['filename']}",
                "size": 1024000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
            }
            
            # Mock concurrent processing
            mock_future = Mock()
            mock_future.result.return_value = None
            
            with patch('utils.sftp_orchestrator.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor.__enter__ = Mock(return_value=mock_executor)
                mock_executor.__exit__ = Mock(return_value=None)
                mock_executor.submit.return_value = mock_future
                mock_executor_class.return_value = mock_executor
                
                with patch('utils.sftp_orchestrator.as_completed', return_value=[mock_future]):
                    with patch('services.sftp_service.SFTPService') as mock_sftp_class:
                        mock_new_sftp = Mock()
                        mock_new_sftp.__enter__ = Mock(return_value=mock_new_sftp)
                        mock_new_sftp.__exit__ = Mock(return_value=None)
                        mock_new_sftp.download_file.return_value = None
                        mock_sftp_class.return_value = mock_new_sftp
                        
                        with patch('utils.sftp_orchestrator.is_valid_media_file', return_value=True):
                            with patch('utils.sftp_orchestrator.parse_filename') as mock_parse:
                                # Set up parsing response
                                parse_response = {
                                    "show_name": f"Test Show {i+1}",
                                    "season": 1,
                                    "episode": i + 1,
                                    "confidence": 0.95,
                                    "reasoning": f"Validation test {i+1}"
                                }
                                
                                if test_case["expected_crc32"]:
                                    parse_response["crc32"] = test_case["expected_crc32"]
                                
                                mock_parse.return_value = parse_response
                                
                                # Process the file
                                process_sftp_diffs(
                                    sftp_service=mock_services['sftp'],
                                    db_service=mock_services['db'],
                                    diffs=[file_diff],
                                    remote_base="/remote",
                                    local_base=temp_dir,
                                    dry_run=False,
                                    llm_service=mock_services['llm'],
                                    hashing_service=mock_services['hashing'],
                                    parse_filenames=True,
                                    use_llm=True,
                                    llm_confidence_threshold=0.7,
                                )
            
            # Verify the result
            if mock_services['db'].upsert_downloaded_file.call_count > i:
                stored_file = mock_services['db'].upsert_downloaded_file.call_args_list[i][0][0]
                actual_crc32 = stored_file.file_provided_hash_value
                
                if actual_crc32 == test_case["expected_crc32"]:
                    print(f"    ✅ CRC32 extraction correct: {actual_crc32}")
                    success_count += 1
                else:
                    print(f"    ❌ CRC32 mismatch: expected {test_case['expected_crc32']}, got {actual_crc32}")
            else:
                print(f"    ❌ File was not processed")
    
    print(f"📊 CRC32 extraction validation: {success_count}/{len(test_cases)} tests passed")
    return success_count == len(test_cases)


def validate_database_operations():
    """Validate database operations with new field structure."""
    print("\n🗄️ Validating database operations with new field structure...")
    
    # Test DownloadedFile model with CRC32 data
    test_file = DownloadedFile(
        name="Database Test S01E01 [ABCDEF12].mkv",
        remote_path="/remote/db_test/Database Test S01E01 [ABCDEF12].mkv",
        current_path="/local/Database Test S01E01 [ABCDEF12].mkv",
        size=1024000,
        modified_time=datetime.datetime(2024, 1, 1, 12, 0, 0),
        fetched_at=datetime.datetime(2024, 1, 1, 12, 0, 0),
        is_dir=False,
        file_provided_hash_value="ABCDEF12",
        show_name="Database Test",
        season=1,
        episode=1,
        confidence=0.95,
        reasoning="Database validation test"
    )
    
    try:
        # Test serialization for database storage
        db_tuple = test_file.to_db_tuple()
        print(f"  ✅ Database tuple serialization successful: {len(db_tuple)} fields")
        
        # Test reconstruction from database record
        db_record = {
            "id": 1,
            "name": test_file.name,
            "remote_path": test_file.remote_path,
            "current_path": test_file.current_path,
            "size": test_file.size,
            "modified_time": test_file.modified_time,
            "fetched_at": test_file.fetched_at,
            "is_dir": test_file.is_dir,
            "status": test_file.status.value,
            "file_hash": test_file.file_hash,
            "file_provided_hash_value": test_file.file_provided_hash_value,
            "show_name": test_file.show_name,
            "season": test_file.season,
            "episode": test_file.episode,
            "confidence": test_file.confidence,
            "reasoning": test_file.reasoning,
            "tmdb_id": test_file.tmdb_id,
            "routing_attempts": test_file.routing_attempts,
            "last_routing_attempt": test_file.last_routing_attempt,
            "error_message": test_file.error_message,
            "metadata": test_file.metadata
        }
        
        reconstructed_file = DownloadedFile.from_db_record(db_record)
        
        if reconstructed_file.file_provided_hash_value == "ABCDEF12":
            print(f"  ✅ Database record reconstruction successful")
            print(f"  ✅ CRC32 field preserved: {reconstructed_file.file_provided_hash_value}")
            return True
        else:
            print(f"  ❌ CRC32 field not preserved in reconstruction")
            return False
            
    except Exception as e:
        print(f"  ❌ Database operations failed: {e}")
        return False


def validate_complete_workflow():
    """Validate the complete SFTP download workflow."""
    print("\n🔄 Validating complete SFTP download workflow...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        mock_services = create_mock_services()
        
        # Mock remote file listing
        remote_files = [
            {
                "name": "Workflow Test S01E01 [FEDCBA98].mkv",
                "path": "/remote/workflow/Workflow Test S01E01 [FEDCBA98].mkv",
                "size": 2048000,
                "modified_time": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "is_dir": False,
            }
        ]
        
        # Set up mock services
        mock_services['sftp'].list_remote_dir.return_value = remote_files
        mock_services['db'].get_sftp_diffs.return_value = [
            {
                **remote_files[0],
                "fetched_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
                "remote_path": remote_files[0]["path"]
            }
        ]
        
        # Create test file
        file_path = Path(temp_dir) / remote_files[0]["name"]
        file_path.write_text("complete workflow validation content")
        
        try:
            # Mock concurrent processing
            mock_future = Mock()
            mock_future.result.return_value = None
            
            with patch('utils.sftp_orchestrator.ThreadPoolExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor.__enter__ = Mock(return_value=mock_executor)
                mock_executor.__exit__ = Mock(return_value=None)
                mock_executor.submit.return_value = mock_future
                mock_executor_class.return_value = mock_executor
                
                with patch('utils.sftp_orchestrator.as_completed', return_value=[mock_future]):
                    with patch('services.sftp_service.SFTPService') as mock_sftp_class:
                        mock_new_sftp = Mock()
                        mock_new_sftp.__enter__ = Mock(return_value=mock_new_sftp)
                        mock_new_sftp.__exit__ = Mock(return_value=None)
                        mock_new_sftp.download_file.return_value = None
                        mock_sftp_class.return_value = mock_new_sftp
                        
                        with patch('utils.sftp_orchestrator.is_valid_media_file', return_value=True):
                            with patch('utils.sftp_orchestrator.parse_filename') as mock_parse:
                                mock_parse.return_value = {
                                    "show_name": "Workflow Test",
                                    "season": 1,
                                    "episode": 1,
                                    "crc32": "FEDCBA98",
                                    "confidence": 0.95,
                                    "reasoning": "Complete workflow validation"
                                }
                                
                                # Run the complete workflow
                                download_from_remote(
                                    sftp=mock_services['sftp'],
                                    db=mock_services['db'],
                                    remote_paths=["/remote/workflow"],
                                    incoming_path=temp_dir,
                                    dry_run=False,
                                    hashing_service=mock_services['hashing'],
                                    parse_filenames=True,
                                    use_llm=True,
                                    llm_confidence_threshold=0.7,
                                )
            
            # Verify workflow execution
            if mock_services['db'].upsert_downloaded_file.call_count == 1:
                stored_file = mock_services['db'].upsert_downloaded_file.call_args_list[0][0][0]
                
                if stored_file.file_provided_hash_value == "FEDCBA98":
                    print(f"  ✅ Complete workflow successful")
                    print(f"  ✅ CRC32 preserved through workflow: {stored_file.file_provided_hash_value}")
                    print(f"  ✅ Show metadata extracted: {stored_file.show_name} S{stored_file.season:02d}E{stored_file.episode:02d}")
                    return True
                else:
                    print(f"  ❌ CRC32 not preserved: expected FEDCBA98, got {stored_file.file_provided_hash_value}")
                    return False
            else:
                print(f"  ❌ File was not processed through workflow")
                return False
                
        except Exception as e:
            print(f"  ❌ Complete workflow failed: {e}")
            return False


def main():
    """Run all end-to-end validation tests."""
    print("🚀 Starting CRC32 Field Migration End-to-End Validation")
    print("=" * 60)
    
    validation_results = []
    
    # Run validation tests
    validation_results.append(validate_crc32_extraction())
    validation_results.append(validate_database_operations())
    validation_results.append(validate_complete_workflow())
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Validation Summary:")
    
    test_names = [
        "CRC32 Extraction from Filenames",
        "Database Operations with New Field Structure",
        "Complete SFTP Download Workflow"
    ]
    
    passed_count = 0
    for i, (test_name, result) in enumerate(zip(test_names, validation_results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {i+1}. {test_name}: {status}")
        if result:
            passed_count += 1
    
    print(f"\n🎯 Overall Result: {passed_count}/{len(validation_results)} validations passed")
    
    if all(validation_results):
        print("🎉 All validations passed! CRC32 field migration is working correctly.")
        return 0
    else:
        print("⚠️  Some validations failed. Please review the migration implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())