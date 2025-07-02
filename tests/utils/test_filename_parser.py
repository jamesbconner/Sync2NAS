import pytest
from utils.filename_parser import parse_filename

class MockLLM:
    def __init__(self, result=None, raise_exc=False):
        self.result = result
        self.raise_exc = raise_exc
    def parse_filename(self, filename):
        if self.raise_exc:
            raise Exception('LLM error')
        return self.result

def test_regex_parses_standard_format():
    """Test that parse_filename extracts show, season, and episode from S01E01 format."""
    result = parse_filename("Show.Name.S01E01.1080p.mkv")
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 1
    assert result["episode"] == 1
    assert result["confidence"] == 0.6

def test_regex_parses_alternate_format():
    """Test that parse_filename extracts info from alternate format with season/episode words."""
    result = parse_filename("Show Name - 1st Season - 1.mkv")
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 1
    assert result["episode"] == 1

def test_regex_handles_tags_and_metadata():
    """Test that parse_filename ignores tags/metadata in brackets or parentheses."""
    result = parse_filename("Show.Name.[Group].S01E01.mkv")
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 1
    assert result["episode"] == 1

def test_regex_handles_no_match():
    """Test that parse_filename returns only show_name and low confidence if no pattern matches."""
    result = parse_filename("RandomFile.txt")
    assert result["show_name"].lower() == "randomfile"
    assert result["season"] is None
    assert result["episode"] is None
    assert result["confidence"] == 0.1

def test_llm_high_confidence():
    """Test that parse_filename uses LLM result if confidence is high enough."""
    llm = MockLLM(result={"show_name": "LLM Show", "season": 2, "episode": 3, "confidence": 0.95, "reasoning": "LLM"})
    result = parse_filename("anything.mkv", llm_service=llm, llm_confidence_threshold=0.7)
    assert result["show_name"] == "LLM Show"
    assert result["season"] == 2
    assert result["episode"] == 3
    assert result["confidence"] == 0.95
    assert result["reasoning"] == "LLM"

def test_llm_low_confidence_fallbacks_to_regex():
    """Test that parse_filename falls back to regex if LLM confidence is too low."""
    llm = MockLLM(result={"show_name": "LLM Show", "season": 2, "episode": 3, "confidence": 0.5, "reasoning": "LLM"})
    result = parse_filename("Show.Name.S01E01.1080p.mkv", llm_service=llm, llm_confidence_threshold=0.7)
    # Should fallback to regex result
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 1
    assert result["episode"] == 1
    assert result["confidence"] == 0.6

def test_llm_exception_fallbacks_to_regex():
    """Test that parse_filename falls back to regex if LLM raises an exception."""
    llm = MockLLM(raise_exc=True)
    result = parse_filename("Show.Name.S01E01.1080p.mkv", llm_service=llm)
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 1
    assert result["episode"] == 1
    assert result["confidence"] == 0.6

def test_filename_parser_basic():
    """Basic placeholder test for utils/filename_parser.py functionality."""
    # TODO: Add tests for utils/filename_parser.py
    assert True 