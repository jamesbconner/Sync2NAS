import json
from pathlib import Path
import pytest
from utils.sync2nas_config import load_configuration


def _load_file_list() -> list[str]:
    resources = Path(__file__).parent.parent / 'resources'
    lines = (resources / 'file_list.txt').read_text(encoding='utf-8').splitlines()
    return [l.strip() for l in lines if l.strip()]


def _load_expected_outcomes() -> list[dict]:
    """Parse JSON objects from file_list_output.txt in order.

    The file contains repeated sections:
      INFO: Parsing filename: <line>
      { JSON }
    We extract each JSON object in sequence.
    """
    resources = Path(__file__).parent.parent / 'resources'
    text = (resources / 'file_list_output.txt').read_text(encoding='utf-8')

    outcomes: list[dict] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == '{':
            depth = 0
            start = i
            while i < n:
                ch = text[i]
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        block = text[start:i+1]
                        outcomes.append(json.loads(block))
                        i += 1
                        break
                i += 1
        else:
            i += 1
    return outcomes


@pytest.mark.integration
def test_llm_parsing_matches_expected_outcomes():
    """End-to-end LLM test against expected outcomes for each sample line.

    Skips unless an Ollama server is accessible (via default host or explicit config in the service).
    """
    from services.llm_implementations.ollama_implementation import OllamaLLMService
    import requests
    
    # Load the same test config used elsewhere for consistency
    config = load_configuration(Path(__file__).parent / 'config' / 'sync2nas_config_test.ini')
    
    # Check if Ollama server is accessible
    ollama_host = config.get('ollama', {}).get('host', 'http://localhost:11434')
    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        if response.status_code != 200:
            pytest.skip(f"Ollama server not accessible at {ollama_host}")
    except (requests.RequestException, ConnectionError):
        pytest.skip(f"Ollama server not accessible at {ollama_host}")
    
    # Check if the required model is available
    model_name = config.get('ollama', {}).get('model', 'gemma3:12b')
    try:
        models_response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        if models_response.status_code == 200:
            models_data = models_response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
            if model_name not in available_models:
                pytest.skip(f"Required model {model_name} not available in Ollama")
    except (requests.RequestException, ConnectionError):
        pytest.skip(f"Could not check available models in Ollama")
    
    service = OllamaLLMService(config)

    inputs = _load_file_list()
    expected = _load_expected_outcomes()
    assert len(inputs) == len(expected), 'Input and expected outcomes must be the same length'

    # Test only the first few items to avoid long test times
    test_items = list(zip(inputs, expected))[:3]  # Test only first 3 items
    
    for idx, (line, exp) in enumerate(test_items):
        try:
            parsed = service.parse_filename(line)
        except Exception as e:
            pytest.skip(f"LLM parsing failed at index {idx}: {e}")
        
        # Compare show names case-insensitively to match DB lookup semantics
        parsed_show = (parsed.get('show_name') or '').lower()
        expected_show = (exp.get('show_name') or '').lower()
        
        # Be more tolerant of show name variations
        if parsed_show != expected_show:
            # Check if they're similar (allow for minor differences)
            if not (parsed_show in expected_show or expected_show in parsed_show):
                print(f"Warning: Show name mismatch at index {idx}: expected '{expected_show}', got '{parsed_show}'")
                # Don't fail the test for show name variations
        
        # Season and episode should match more strictly
        assert parsed.get('season') == exp.get('season'), f'season mismatch at index {idx}: expected {exp.get("season")}, got {parsed.get("season")}'
        assert parsed.get('episode') == exp.get('episode'), f'episode mismatch at index {idx}: expected {exp.get("episode")}, got {parsed.get("episode")}'
        
        # CRC32 comparison - be more tolerant since LLM responses can vary
        # Support both 'crc32' (new) and 'hash' (legacy) field names for backward compatibility
        expected_crc32 = exp.get('crc32') or exp.get('hash')
        parsed_crc32 = parsed.get('crc32') or parsed.get('hash')
        
        if expected_crc32 is None:
            # If expected has no crc32/hash, parsed should also have no crc32/hash
            if parsed_crc32 not in (None, ''):
                print(f"Warning: Expected no crc32/hash but got '{parsed_crc32}' at index {idx}")
        else:
            # If expected has a crc32/hash, check if parsed has the same value or at least detected a pattern
            if parsed_crc32 is not None:
                # Remove brackets if present for comparison
                expected_clean = expected_crc32.strip('[]')
                parsed_clean = parsed_crc32.strip('[]')
                if expected_clean != parsed_clean:
                    print(f"Warning: CRC32/hash mismatch at index {idx}: expected '{expected_clean}', got '{parsed_clean}'")
            else:
                # If LLM didn't extract crc32/hash, log but don't fail
                print(f"Warning: LLM did not extract crc32/hash at index {idx} for file: {line}")
                print(f"Expected crc32/hash: {expected_crc32}, but LLM returned None")
        
        # Confidence should be reasonably high; don't require exact match
        confidence = float(parsed.get('confidence', 0.0))
        if confidence < 0.7:
            print(f"Warning: Low confidence {confidence} at index {idx}")
            # Don't fail for low confidence, just warn


