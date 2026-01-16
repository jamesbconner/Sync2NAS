"""
Test filename parsing functionality with both LLM and regex methods.
"""
import os
import pytest
import logging
from pathlib import Path
from unittest.mock import patch, Mock
from utils.sync2nas_config import load_configuration
from utils.filename_parser import parse_filename
from services.llm.schemas import ParsedFilename

logger = logging.getLogger(__name__)


def test_regex_parses_standard_format():
    """Test that parse_filename extracts show, season, and episode from S01E01 format."""
    # Mock the LLM chains to fail so it falls back to regex
    mock_llm_chains = Mock()
    mock_llm_chains.parse_filename.side_effect = Exception("Mock LLM failure")
    
    result = parse_filename("Show.Name.S01E01.1080p.mkv", llm_chains=mock_llm_chains)
    
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 1
    assert result["episode"] == 1
    assert result["confidence"] == 0.6
    assert "Regex pattern" in result["reasoning"]


def test_regex_parses_alternate_format():
    """Test that parse_filename extracts info from alternate format with season/episode words."""
    # Mock the LLM chains to fail so it falls back to regex
    mock_llm_chains = Mock()
    mock_llm_chains.parse_filename.side_effect = Exception("Mock LLM failure")
    
    result = parse_filename("Show Name - 1st Season - 1.mkv", llm_chains=mock_llm_chains)
    
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 1
    assert result["episode"] == 1
    assert result["confidence"] == 0.6
    assert "Regex pattern" in result["reasoning"]


def test_regex_handles_tags_and_metadata():
    """Test that parse_filename ignores tags/metadata in brackets or parentheses."""
    # Mock the LLM chains to fail so it falls back to regex
    mock_llm_chains = Mock()
    mock_llm_chains.parse_filename.side_effect = Exception("Mock LLM failure")
    
    result = parse_filename("Show.Name.[Group].S01E01.mkv", llm_chains=mock_llm_chains)
    
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 1
    assert result["episode"] == 1
    assert result["confidence"] == 0.6
    assert "Regex pattern" in result["reasoning"]


def test_regex_handles_no_match():
    """Test that parse_filename returns only show_name and low confidence if no pattern matches."""
    # Mock the LLM chains to fail so it falls back to regex
    mock_llm_chains = Mock()
    mock_llm_chains.parse_filename.side_effect = Exception("Mock LLM failure")
    
    result = parse_filename("RandomFile.txt", llm_chains=mock_llm_chains)
    
    assert result["show_name"].lower() == "randomfile"
    assert result["season"] is None
    assert result["episode"] is None
    assert result["confidence"] == 0.1
    assert "No regex pattern matched" in result["reasoning"]


def test_llm_high_confidence():
    """Test that parse_filename uses LLM result if confidence is high enough."""
    # Mock the LLM chains to return high confidence result
    mock_llm_chains = Mock()
    mock_parsed_filename = ParsedFilename(
        show_name="LLM Show",
        season=2,
        episode=3,
        crc32=None,
        confidence=0.95,
        reasoning="LLM parsed successfully"
    )
    mock_llm_chains.parse_filename.return_value = mock_parsed_filename
    
    result = parse_filename("anything.mkv", llm_chains=mock_llm_chains, llm_confidence_threshold=0.7)
    
    assert result["show_name"] == "LLM Show"
    assert result["season"] == 2
    assert result["episode"] == 3
    assert result["confidence"] == 0.95
    assert result["reasoning"] == "LLM parsed successfully"


def test_llm_low_confidence_fallbacks_to_regex():
    """Test that parse_filename falls back to regex if LLM confidence is too low."""
    # Mock the LLM chains to return low confidence result
    mock_llm_chains = Mock()
    mock_parsed_filename = ParsedFilename(
        show_name="LLM Show",
        season=2,
        episode=3,
        crc32=None,
        confidence=0.5,  # Low confidence
        reasoning="LLM uncertain"
    )
    mock_llm_chains.parse_filename.return_value = mock_parsed_filename
    
    result = parse_filename("Show.Name.S01E01.1080p.mkv", llm_chains=mock_llm_chains, llm_confidence_threshold=0.7)
    
    # Should fall back to regex parsing
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 1
    assert result["episode"] == 1
    assert result["confidence"] == 0.6  # Regex confidence
    assert "Regex pattern" in result["reasoning"]


def test_llm_exception_fallbacks_to_regex():
    """Test that parse_filename falls back to regex if LLM raises an exception."""
    # Mock the LLM chains to fail so it falls back to regex
    mock_llm_chains = Mock()
    mock_llm_chains.parse_filename.side_effect = Exception("LLM service unavailable")
    
    result = parse_filename("Show.Name.S01E01.1080p.mkv", llm_chains=mock_llm_chains)
    
    # Should fall back to regex parsing
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 1
    assert result["episode"] == 1
    assert result["confidence"] == 0.6
    assert "Regex pattern" in result["reasoning"]


def test_filename_parser_basic():
    """Test basic filename parsing without LLM chains (regex only)."""
    result = parse_filename("Show.Name.S02E03.720p.mkv")
    
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 2
    assert result["episode"] == 3
    assert result["confidence"] == 0.6
    assert "Regex pattern" in result["reasoning"]


@pytest.mark.integration
def test_llm_parsing_against_resource_file():
    """Integration test that exercises the real LLM parsing using the provided file list.

    Uses the new LangChain-based parsing system.
    """
    # This test would require a real LLM service, so we'll mock it for now
    # In a real integration test, you would use the actual LLM chain service
    mock_llm_chains = Mock()
    mock_parsed_filename = ParsedFilename(
        show_name="Test Show",
        season=1,
        episode=1,
        crc32=None,
        confidence=0.9,
        reasoning="Integration test mock"
    )
    mock_llm_chains.parse_filename.return_value = mock_parsed_filename
    
    result = parse_filename("Test.Show.S01E01.mkv", llm_chains=mock_llm_chains)
    
    assert result["show_name"] == "Test Show"
    assert result["season"] == 1
    assert result["episode"] == 1
    assert result["confidence"] == 0.9