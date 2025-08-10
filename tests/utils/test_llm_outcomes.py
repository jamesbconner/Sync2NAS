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
    # Load the same test config used elsewhere for consistency
    config = load_configuration(Path(__file__).parent / 'config' / 'sync2nas_config_test.ini')
    service = OllamaLLMService(config)

    inputs = _load_file_list()
    expected = _load_expected_outcomes()
    assert len(inputs) == len(expected), 'Input and expected outcomes must be the same length'

    for idx, (line, exp) in enumerate(zip(inputs, expected)):
        parsed = service.parse_filename(line)
        assert parsed.get('show_name') == exp.get('show_name'), f'show_name mismatch at index {idx}'
        assert parsed.get('season') == exp.get('season'), f'season mismatch at index {idx}'
        assert parsed.get('episode') == exp.get('episode'), f'episode mismatch at index {idx}'
        # Only assert hash if expected provides one
        if exp.get('hash') is None:
            assert parsed.get('hash') in (None, ''), f'hash should be None at index {idx}'
        else:
            assert parsed.get('hash') == exp.get('hash'), f'hash mismatch at index {idx}'
        # Confidence should be reasonably high; don't require exact match
        assert float(parsed.get('confidence', 0.0)) >= 0.7, f'confidence too low at index {idx}'


