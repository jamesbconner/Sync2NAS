import os
import sys
import logging
import pytest
from unittest.mock import patch, MagicMock
from utils.logging_config import setup_logging

def test_setup_logging_verbosity_0():
    """Test that verbosity 0 disables all logging."""
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        setup_logging(verbosity=0)
        
        # Verify logger was configured correctly
        mock_logger.setLevel.assert_called_once_with(logging.CRITICAL + 1)
        mock_logger.handlers.clear.assert_called_once()
        # No handlers should be added for verbosity 0
        assert mock_logger.addHandler.call_count == 0

def test_setup_logging_verbosity_1():
    """Test that verbosity 1 sets INFO level."""
    with patch('logging.getLogger') as mock_get_logger, \
         patch('logging.StreamHandler') as mock_stream_handler:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_handler = MagicMock()
        mock_stream_handler.return_value = mock_handler
        
        setup_logging(verbosity=1)
        
        # Verify logger was configured correctly
        mock_logger.setLevel.assert_called_once_with(logging.INFO)
        mock_logger.handlers.clear.assert_called_once()
        # Should add console handler
        mock_logger.addHandler.assert_called_once_with(mock_handler)
        mock_handler.setFormatter.assert_called_once()
        mock_handler.setLevel.assert_called_once_with(logging.INFO)

def test_setup_logging_verbosity_2():
    """Test that verbosity >1 sets DEBUG level."""
    with patch('logging.getLogger') as mock_get_logger, \
         patch('logging.StreamHandler') as mock_stream_handler:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_handler = MagicMock()
        mock_stream_handler.return_value = mock_handler
        
        setup_logging(verbosity=2)
        
        # Verify logger was configured correctly
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)
        mock_logger.handlers.clear.assert_called_once()
        # Should add console handler
        mock_logger.addHandler.assert_called_once_with(mock_handler)
        mock_handler.setFormatter.assert_called_once()
        mock_handler.setLevel.assert_called_once_with(logging.DEBUG)

def test_setup_logging_with_file():
    """Test that file logging is configured when logfile is provided."""
    with patch('logging.getLogger') as mock_get_logger, \
         patch('logging.StreamHandler') as mock_stream_handler, \
         patch('logging.FileHandler') as mock_file_handler:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_console_handler = MagicMock()
        mock_file_handler_instance = MagicMock()
        mock_stream_handler.return_value = mock_console_handler
        mock_file_handler.return_value = mock_file_handler_instance
        
        setup_logging(verbosity=1, logfile="test.log")
        
        # Verify both console and file handlers were added
        assert mock_logger.addHandler.call_count == 2
        mock_file_handler.assert_called_once_with("test.log", encoding='utf-8')
        mock_file_handler_instance.setFormatter.assert_called_once()
        mock_file_handler_instance.setLevel.assert_called_once_with(logging.INFO)

def test_setup_logging_command_line_logging():
    """Test that command line and working directory are logged."""
    with patch('logging.getLogger') as mock_get_logger, \
         patch('sys.argv', ['test.py', '--verbose']), \
         patch('os.getcwd', return_value='/test/dir'):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        setup_logging(verbosity=1)
        
        # Verify command line and working directory were logged
        mock_logger.info.assert_any_call("Command line: test.py --verbose")
        mock_logger.info.assert_any_call("Current working directory: /test/dir")
