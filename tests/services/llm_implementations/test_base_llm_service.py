import pytest
from services.llm_implementations.base_llm_service import BaseLLMService

class DummyLLM(BaseLLMService):
    def parse_filename(self, filename, max_tokens=150):
        return {"show_name": "Show", "season": 1, "episode": 2, "confidence": 0.9, "reasoning": "dummy"}
    
    def suggest_short_dirname(self, long_name: str, max_length: int = 20) -> str:
        return long_name[:max_length]
    
    def suggest_short_filename(self, long_name: str, max_length: int = 20) -> str:
        return long_name[:max_length]
    
    def suggest_show_name(self, show_name: str, detailed_results: list) -> dict:
        """Suggest the best show match from TMDB results."""
        if not detailed_results:
            return {
                "tmdb_id": None,
                "show_name": show_name,
                "confidence": 0.1,
                "reasoning": "No results available"
            }
        
        # Return the first result as the best match
        best_match = detailed_results[0]
        return {
            "tmdb_id": best_match.get("id"),
            "show_name": best_match.get("name", show_name),
            "confidence": 0.9,
            "reasoning": "Dummy LLM selected first result"
        }

def test_create_filename_parsing_prompt():
    """Test that _create_filename_parsing_prompt returns a prompt string containing the filename."""
    llm = DummyLLM()
    prompt = llm._create_filename_parsing_prompt("Show.Name.S01E01.mkv")
    assert "Show.Name.S01E01.mkv" in prompt
    assert "extract" in prompt.lower()

def test_validate_and_clean_result_valid():
    """Test that _validate_and_clean_result returns cleaned and validated result for valid input."""
    llm = DummyLLM()
    result = llm._validate_and_clean_result({"show_name": "Test", "season": "1", "episode": "2", "confidence": "0.8", "reasoning": "ok"}, "file.mkv")
    assert result["show_name"] == "Test"
    assert result["season"] == 1
    assert result["episode"] == 2
    assert result["confidence"] == 0.8
    assert result["reasoning"] == "ok"

def test_validate_and_clean_result_invalid_types():
    """Test that _validate_and_clean_result falls back if types are invalid."""
    llm = DummyLLM()
    result = llm._validate_and_clean_result({"show_name": "Test", "season": "notanint", "episode": "2", "confidence": "0.8"}, "file.mkv")
    assert result["confidence"] == 0.1
    assert result["season"] is None

def test_validate_and_clean_result_empty_show_name():
    """Test that _validate_and_clean_result falls back if show_name is empty."""
    llm = DummyLLM()
    result = llm._validate_and_clean_result({"show_name": "", "season": 1, "episode": 2, "confidence": 0.8}, "file.mkv")
    assert result["confidence"] == 0.1
    assert result["show_name"] == "file"

def test_fallback_parse_matches_pattern():
    """Test that _fallback_parse extracts show, season, and episode from S01E01 pattern."""
    llm = DummyLLM()
    result = llm._fallback_parse("Show.Name.S01E01.mkv")
    assert result["show_name"].lower() == "show name"
    assert result["season"] == 1
    assert result["episode"] == 1
    assert result["confidence"] == 0.5

def test_fallback_parse_no_pattern():
    """Test that _fallback_parse returns only show_name and low confidence if no pattern matches."""
    llm = DummyLLM()
    result = llm._fallback_parse("RandomFile.txt")
    assert result["show_name"].lower() == "randomfile"
    assert result["season"] is None
    assert result["confidence"] == 0.1

def test_clean_filename_for_llm():
    """Test that _clean_filename_for_llm removes extensions, tags, and normalizes delimiters."""
    llm = DummyLLM()
    cleaned = llm._clean_filename_for_llm("Show.Name.[Group].S01E01.mkv")
    assert "[Group]" not in cleaned
    assert ".mkv" not in cleaned
    assert "Show Name" in cleaned

def test_batch_parse_filenames_calls_parse_filename():
    """Test that batch_parse_filenames calls parse_filename for each filename and returns results."""
    llm = DummyLLM()
    files = ["Show1.S01E01.mkv", "Show2.S01E02.mkv"]
    results = llm.batch_parse_filenames(files)
    assert len(results) == 2
    assert results[0]["filename"] == "Show1.S01E01.mkv"
    assert results[1]["filename"] == "Show2.S01E02.mkv"
    assert results[0]["parsed"]["show_name"] == "Show"

def test_base_llm_service_basic():
    # TODO: Add tests for services/llm_implementations/base_llm_service.py
    assert True 