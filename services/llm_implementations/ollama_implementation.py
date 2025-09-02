import logging
import json
import re
from pydantic import BaseModel, Field, ValidationError
import datetime
import os as _os
from typing import Dict, Any, List, Union
from configparser import ConfigParser
from ollama import Client
from utils.sync2nas_config import load_configuration, get_config_value
from services.llm_implementations.base_llm_service import BaseLLMService

logger = logging.getLogger(__name__)

class ParsedFilename(BaseModel):
    show_name: str = Field(..., description="Full show name, as extracted from filename")
    season: int | None = Field(..., description="Season number as integer, or null if not present")
    episode: int = Field(..., description="Episode number as integer, or null if not present")
    crc32: str | None = Field(None, description="CRC32 checksum if present in the filename. It is always exactly 8 hex characters (0-9A-F), without brackets.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence between 0.0 and 1.0")
    reasoning: str = Field(..., description="Explanation of field choices and confidence")

class SuggestedShowName(BaseModel):
    tmdb_id: int = Field(..., description="TMDB ID of the show")
    show_name: str = Field(..., description="Full show name, as extracted from filename")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence between 0.0 and 1.0")
    reasoning: str = Field(..., description="Explanation of field choices and confidence")

class SuggestedDirname(BaseModel):
    short_name: str = Field(..., description="Shortened directory name within character limit")
    reasoning: str = Field(..., description="Brief explanation of shortening choices")

class SuggestedFilename(BaseModel):
    short_name: str = Field(..., description="Shortened filename within character limit, preserving extension")
    reasoning: str = Field(..., description="Brief explanation of shortening choices")

class OllamaLLMService(BaseLLMService):
    """
    LLM service implementation using a local Ollama server and model.

    Provides filename parsing, directory/filename suggestion, and show name selection using LLM.

    Attributes:
        config (dict): Configuration object.
        model (str): Model name used by Ollama.
        client (Client): Ollama client instance.
    """
    def __init__(self, config: Union[ConfigParser, Dict[str, Dict[str, Any]]]):
        """
        Initialize the Ollama LLM service.
        Args:
            config: Loaded configuration object (ConfigParser or normalized dict)
        """
        self.config = config
        self.model = get_config_value(config, 'ollama', 'model', 'qwen3:14b')
        
        # Context window for input tokens (model-dependent). Default to 4096 if not specified.
        num_ctx_raw = get_config_value(config, 'ollama', 'num_ctx', '4096')
        try:
            self.num_ctx = int(num_ctx_raw)
        except (ValueError, TypeError):
            self.num_ctx = 4096
            
        # Use Ollama default host behavior (localhost) without requiring host configuration
        self.host = get_config_value(config, 'ollama', 'host', 'http://localhost:11434')
        self.client = Client(host=self.host)
        logger.info(f"Ollama LLM service initialized with model: {self.model}")
        logger.debug(f"Ollama client host: {get_config_value(self.config, 'ollama', 'host', '(default)')}")

    def _dump_failure_artifacts(self, context: str, prompt: str, raw_text: str | None) -> None:
        """Persist prompt and raw response for debugging when parsing fails."""
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            base_dir = _os.path.join("testing", "llm_failures")
            _os.makedirs(base_dir, exist_ok=True)
            base = f"{context}_{ts}"
            prompt_path = _os.path.join(base_dir, f"{base}.prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(prompt)
            if raw_text is not None:
                resp_path = _os.path.join(base_dir, f"{base}.response.txt")
                with open(resp_path, "w", encoding="utf-8") as f:
                    f.write(raw_text)
            logger.info(f"LLM failure artifacts written: {prompt_path}{' and response file' if raw_text else ''}")
        except Exception as art_exc:
            logger.debug(f"Failed to write LLM artifacts: {art_exc}")

    def parse_filename(self, filename: str, max_tokens: int = 4096) -> Dict[str, Any]:
        """
        Parse a filename using Ollama LLM to extract show metadata.
        Args:
            filename: Raw filename to parse
            max_tokens: Maximum tokens for LLM response
        Returns:
            dict: Parsed metadata
        """
        logger.info(f"Parsing filename with Ollama LLM: {filename} (model={self.model})")
        #cleaned_filename = self._clean_filename_for_llm(filename)
        #prompt = self.load_prompt('parse_filename').format(filename=cleaned_filename)
        prompt = self.load_prompt('parse_filename').format(filename=filename)
        try:
            # Use format parameter with model_json_schema() for models that support it (like qwen3:14b)
            # This ensures proper structured output including all required fields
            use_format = not str(self.model).lower().startswith("gpt-oss")
            format_schema = ParsedFilename.model_json_schema() if use_format else None

            def _call_ollama(format_arg):
                kwargs = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens, "temperature": 0.0, "num_ctx": self.num_ctx},
                }
                if format_arg is not None:
                    kwargs["format"] = format_arg
                logger.debug(
                    f"LLM generate() call: model={kwargs['model']}, format={'on' if format_arg else 'off'}, "
                    f"options={kwargs['options']}, prompt_len={len(prompt)}"
                )
                logger.debug(f"Prompt head: {prompt[:400]}")
                return self.client.generate(**kwargs)

            start_ts = datetime.datetime.now()
            response = _call_ollama(format_schema)
            duration_ms = (datetime.datetime.now() - start_ts).total_seconds() * 1000.0

            # Extract the JSON/string content
            if hasattr(response, 'response'):
                content = response.response
            elif isinstance(response, dict) and 'response' in response:
                content = response['response']
            else:
                content = response

            text = (content or "").strip() if isinstance(content, str) else str(content)
            logger.debug(
                f"LLM response received in {duration_ms:.0f} ms; type={type(response)}, "
                f"text_len={len(text)}"
            )
            if isinstance(response, dict):
                try:
                    logger.debug(f"LLM response dict keys: {list(response.keys())}")
                except Exception:
                    pass
            logger.debug(f"Response head: {text[:400]}")
            if not text and format_schema is not None:
                logger.info("Empty response with format; retrying without format")
                start_ts = datetime.datetime.now()
                response = _call_ollama(None)
                content = response.response if hasattr(response, 'response') else (response.get('response') if isinstance(response, dict) else response)
                text = (content or "").strip() if isinstance(content, str) else str(content)
                logger.debug(
                    f"Retry without format returned text_len={len(text)} in "
                    f"{(datetime.datetime.now() - start_ts).total_seconds() * 1000.0:.0f} ms"
                )

            if not text:
                logger.error("Empty Ollama response after retry; using fallback parser")
                self._dump_failure_artifacts("parse_filename_empty", prompt, None)
                return self._fallback_parse(filename)

            logger.debug(f"Ollama response: {text}")
            # Also print to console for debugging
            print(f"🔍 RAW OLLAMA RESPONSE:")
            print(f"   Model: {self.model}")
            print(f"   Format schema: {'enabled' if format_schema else 'disabled'}")
            print(f"   Response length: {len(text)} characters")
            print(f"   Raw text: {repr(text)}")
            print(f"   Raw text (pretty): {text}")

            # Extract first JSON object in case of extra prose or code fences
            json_text = self._extract_first_json_object(text)
            print(f"🔍 JSON EXTRACTION:")
            print(f"   Extracted JSON: {repr(json_text)}")
            if json_text is None:
                logger.error("No JSON object found in Ollama response; using fallback parser")
                print(f"   ❌ JSON extraction failed!")
                self._dump_failure_artifacts("parse_filename_no_json", prompt, text)
                return self._fallback_parse(filename)

            try:
                result = json.loads(json_text)
                print(f"🔍 JSON PARSING:")
                print(f"   Parsed JSON result: {result}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from Ollama response: {e}")
                print(f"   ❌ JSON parsing failed: {e}")
                self._dump_failure_artifacts("parse_filename_json_error", prompt, text)
                return self._fallback_parse(filename)

            # Strong validation against the Pydantic model to ensure structure/types
            try:
                print(f"🔍 PYDANTIC VALIDATION:")
                print(f"   Input to Pydantic: {result}")
                print(f"   CRC32 field in input: {result.get('crc32', 'NOT_FOUND')}")
                model_instance = ParsedFilename.model_validate(result)
                validated_dict = model_instance.model_dump()
                print(f"   Pydantic validated: {validated_dict}")
                print(f"   CRC32 field after validation: {validated_dict.get('crc32', 'NOT_FOUND')}")
            except ValidationError as e:
                logger.error(f"Pydantic validation failed for Ollama response: {e}")
                print(f"   ❌ Pydantic validation failed: {e}")
                self._dump_failure_artifacts("parse_filename_validation_error", prompt, text)
                return self._fallback_parse(filename)

            parsed_result = self._validate_and_clean_result(validated_dict, filename)
            logger.info(f"Successfully parsed: {parsed_result}")
            return parsed_result
        except Exception as e:
            logger.exception(f"Ollama API error: {e}")
            return self._fallback_parse(filename)

    def _extract_first_json_object(self, content: str) -> str | None:
        """
        Extract the first JSON object from a possibly noisy response.

        Handles code fences and leading/trailing prose. Returns None if not found.
        """
        if not content:
            return None

        # Strip common markdown fences
        fenced = re.sub(r"^```[a-zA-Z0-9]*\n|\n```$", "", content.strip())

        stripped = fenced.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped

        # Brace-balancing scan to capture only the first complete JSON object
        start_index = stripped.find("{")
        if start_index == -1:
            return None

        depth = 0
        in_string = False
        string_char = ""
        i = start_index
        while i < len(stripped):
            ch = stripped[i]
            if in_string:
                if ch == "\\":
                    # Skip escaped character inside string
                    i += 2
                    continue
                if ch == string_char:
                    in_string = False
            else:
                if ch == '"' or ch == "'":
                    in_string = True
                    string_char = ch
                elif ch == '{':
                    if depth == 0:
                        start_index = i
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return stripped[start_index:i+1].strip()
            i += 1

        return None

    def suggest_short_dirname(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable directory name for a given long name using the LLM.
        Fallback to truncation if LLM fails.
        Args:
            long_name: The long name to suggest a short version for.
            max_length: The maximum length of the short name.
        Returns:
            str: A short, human-readable directory name.
        """
        logger.info(f"Suggesting short dirname with Ollama LLM: {long_name} (max={max_length}, model={self.model})")
        prompt = self.load_prompt('suggest_short_dirname')
        prompt = prompt.format(max_length=max_length, long_name=long_name)
        try:
            # Use format parameter with model_json_schema() for structured output
            use_format = not str(self.model).lower().startswith("gpt-oss")
            format_schema = SuggestedDirname.model_json_schema() if use_format else None

            def _call_ollama(format_arg):
                kwargs = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 200, "temperature": 0.1, "num_ctx": self.num_ctx},
                }
                if format_arg is not None:
                    kwargs["format"] = format_arg
                logger.debug(f"LLM dirname generate() call: format={'on' if format_arg else 'off'}")
                return self.client.generate(**kwargs)

            start_ts = datetime.datetime.now()
            response = _call_ollama(format_schema)
            duration_ms = (datetime.datetime.now() - start_ts).total_seconds() * 1000.0

            # Extract the JSON/string content
            if hasattr(response, 'response'):
                content = response.response
            elif isinstance(response, dict) and 'response' in response:
                content = response['response']
            else:
                content = response

            text = (content or "").strip() if isinstance(content, str) else str(content)
            logger.debug(f"LLM dirname response received in {duration_ms:.0f} ms; text_len={len(text)}")
            
            if not text and format_schema is not None:
                logger.info("Empty response with format; retrying without format")
                response = _call_ollama(None)
                content = response.response if hasattr(response, 'response') else (response.get('response') if isinstance(response, dict) else response)
                text = (content or "").strip() if isinstance(content, str) else str(content)

            if not text:
                logger.error("Empty Ollama response for dirname suggestion; using fallback")
                return long_name[:max_length]

            # Extract first JSON object in case of extra prose or code fences
            json_text = self._extract_first_json_object(text)
            if json_text is None:
                logger.error("No JSON object found in dirname response; using fallback")
                return long_name[:max_length]

            try:
                result = json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from dirname response: {e}")
                return long_name[:max_length]

            # Validate against the Pydantic model
            try:
                model_instance = SuggestedDirname.model_validate(result)
                validated_dict = model_instance.model_dump()
                short_name = validated_dict.get('short_name', '').strip()
            except ValidationError as e:
                logger.error(f"Pydantic validation failed for dirname response: {e}")
                return long_name[:max_length]

            # Clean and validate the result
            if short_name:
                # Truncate if needed
                short_name = short_name[:max_length]
                # Remove problematic characters
                short_name = re.sub(r'[^\w\- ]', '', short_name)
                logger.debug(f"LLM recommended dirname: {short_name}")
                return short_name or long_name[:max_length]
            else:
                logger.warning("Empty short_name from LLM; using fallback")
                return long_name[:max_length]
                
        except Exception as e:
            logger.exception(f"LLM dirname error: {e}")
            return long_name[:max_length]

    def suggest_short_filename(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable filename for a given long filename using the LLM.
        Fallback to truncation if LLM fails.
        Args:
            long_name: The long filename to suggest a short version for.
            max_length: The maximum length of the short filename.
        Returns:
            str: A short, human-readable filename.
        """
        logger.info(f"Suggesting short filename with Ollama LLM: {long_name} (max={max_length}, model={self.model})")
        prompt = self.load_prompt('suggest_short_filename')
        prompt = prompt.format(max_length=max_length, long_name=long_name)
        try:
            # Use format parameter with model_json_schema() for structured output
            use_format = not str(self.model).lower().startswith("gpt-oss")
            format_schema = SuggestedFilename.model_json_schema() if use_format else None

            def _call_ollama(format_arg):
                kwargs = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 200, "temperature": 0.1, "num_ctx": self.num_ctx},
                }
                if format_arg is not None:
                    kwargs["format"] = format_arg
                logger.debug(f"LLM filename generate() call: format={'on' if format_arg else 'off'}")
                return self.client.generate(**kwargs)

            start_ts = datetime.datetime.now()
            response = _call_ollama(format_schema)
            duration_ms = (datetime.datetime.now() - start_ts).total_seconds() * 1000.0

            # Extract the JSON/string content
            if hasattr(response, 'response'):
                content = response.response
            elif isinstance(response, dict) and 'response' in response:
                content = response['response']
            else:
                content = response

            text = (content or "").strip() if isinstance(content, str) else str(content)
            logger.debug(f"LLM filename response received in {duration_ms:.0f} ms; text_len={len(text)}")
            
            if not text and format_schema is not None:
                logger.info("Empty response with format; retrying without format")
                response = _call_ollama(None)
                content = response.response if hasattr(response, 'response') else (response.get('response') if isinstance(response, dict) else response)
                text = (content or "").strip() if isinstance(content, str) else str(content)

            if not text:
                logger.error("Empty Ollama response for filename suggestion; using fallback")
                return long_name[:max_length]

            # Extract first JSON object in case of extra prose or code fences
            json_text = self._extract_first_json_object(text)
            if json_text is None:
                logger.error("No JSON object found in filename response; using fallback")
                return long_name[:max_length]

            try:
                result = json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from filename response: {e}")
                return long_name[:max_length]

            # Validate against the Pydantic model
            try:
                model_instance = SuggestedFilename.model_validate(result)
                validated_dict = model_instance.model_dump()
                short_name = validated_dict.get('short_name', '').strip()
            except ValidationError as e:
                logger.error(f"Pydantic validation failed for filename response: {e}")
                return long_name[:max_length]

            # Clean and validate the result
            if short_name:
                # Truncate if needed
                short_name = short_name[:max_length]
                # Remove problematic characters (allow dots for extensions)
                short_name = re.sub(r'[^\w\-. ]', '', short_name)
                logger.debug(f"LLM recommended filename: {short_name}")
                return short_name or long_name[:max_length]
            else:
                logger.warning("Empty short_name from LLM; using fallback")
                return long_name[:max_length]
                
        except Exception as e:
            logger.exception(f"LLM filename error: {e}")
            return long_name[:max_length]

    def suggest_show_name(self, show_name: str, detailed_results: list, max_tokens: int = 16384) -> dict:
        """
        Suggest the best show match and English name from TMDB results using the LLM.
        Should return a dict with keys: tmdb_id, show_name
        Args:
            show_name: The original show name.
            detailed_results: A list of detailed TMDB results.
        Returns:
            dict: The best match found by the LLM.
        """
        # Build a summary of candidates for the prompt
        candidates = []
        for det in detailed_results:
            info = det.get('info', {})
            candidates.append({
                'id': info.get('id'),
                'tmdb_id': info.get('id'),
                'name': info.get('name'),
                'original_name': info.get('original_name'),
                'first_air_date': info.get('first_air_date'),
                'overview': info.get('overview'),
                'alternative_titles': det.get('alternative_titles', {}).get('results', [])
            })
        
        logger.debug(f"Candidates: {candidates}")
        
        # Format the prompt with the candidates and execute the LLM
        prompt_template = self.load_prompt('select_show_name')
        candidates_json = json.dumps(candidates, ensure_ascii=False, indent=2)
        prompt = prompt_template.format(show_name=show_name, candidates=candidates_json)
        try:
            use_schema = not str(self.model).lower().startswith("gpt-oss")
            schema = SuggestedShowName.model_json_schema() if use_schema else None

            def _call_ollama(schema_arg):
                kwargs = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens, "temperature": 0.1, "num_ctx": self.num_ctx},
                }
                if schema_arg is not None:
                    kwargs["format"] = schema_arg
                return self.client.generate(**kwargs)

            response = _call_ollama(schema)
            content = response.response if hasattr(response, 'response') else (response.get('response') if isinstance(response, dict) else response)
            text = (content or "").strip() if isinstance(content, str) else str(content)
            if not text and schema is not None:
                logger.info("Empty response with schema for suggest_show_name; retrying without schema")
                response = _call_ollama(None)
                content = response.response if hasattr(response, 'response') else (response.get('response') if isinstance(response, dict) else response)
                text = (content or "").strip() if isinstance(content, str) else str(content)

            # If still empty, try a reinforced prompt variant to encourage immediate JSON
            if not text:
                logger.info("Empty response for suggest_show_name; retrying with reinforced JSON-only instruction")
                reinforced_prompt = prompt + "\nReturn ONLY the raw JSON object on a single line now."
                response = self.client.generate(
                    model=self.model,
                    prompt=reinforced_prompt,
                    stream=False,
                    options={"num_predict": 256, "temperature": 0.1},
                )
                content = response.response if hasattr(response, 'response') else (response.get('response') if isinstance(response, dict) else response)
                text = (content or "").strip() if isinstance(content, str) else str(content)

            if not text:
                raise ValueError("Empty Ollama response for suggest_show_name")

            # Try to parse as JSON; tolerate prose-wrapped JSON
            json_text = self._extract_first_json_object(text) or text
            result = json.loads(json_text)
            logger.debug(f"LLM response: {text}")

            if 'tmdb_id' in result and 'show_name' in result:
                # Ensure confidence and reasoning are present for downstream logic
                if 'confidence' not in result or not isinstance(result.get('confidence'), (int, float)):
                    result['confidence'] = 0.0
                if 'reasoning' not in result:
                    result['reasoning'] = 'LLM provided result without confidence/reasoning; defaulted confidence to 0.0.'
                
                # Handle the special case where LLM indicates no match (tmdb_id = -1)
                if result.get('tmdb_id') == -1:
                    if not candidates:
                        # This is the correct response for empty candidates
                        return result
                    else:
                        # LLM said no match but there are candidates - this might be an error
                        logger.warning(f"LLM returned no match (tmdb_id=-1) but candidates were provided: {len(candidates)} candidates")
                        return result
                
                # Validate that the returned tmdb_id exists in the candidates (if candidates provided)
                if candidates:
                    candidate_ids = [c.get('id') for c in candidates]
                    if result.get('tmdb_id') not in candidate_ids:
                        logger.warning(f"LLM returned tmdb_id {result.get('tmdb_id')} which is not in candidates {candidate_ids}")
                        # This might be the JSON extraction bug - let's log it and fall back
                        first = candidates[0]
                        return {
                            'tmdb_id': first['id'],
                            'show_name': first['name'],
                            'confidence': 0.0,
                            'reasoning': f'LLM returned invalid tmdb_id {result.get("tmdb_id")} not in candidates; fell back to first candidate.'
                        }
                
                return result
            else:
                logger.warning(f"LLM response missing required fields: {result}")
                if candidates:
                    first = candidates[0]
                    return {
                        'tmdb_id': first['id'],
                        'show_name': first['name'],
                        'confidence': 0.0,
                        'reasoning': 'Fell back to first TMDB candidate because LLM response was missing required fields.'
                    }
                else:
                    raise ValueError("No candidates available for fallback")
        except Exception as e:
            logger.exception(f"LLM error: {e}")
            if candidates:
                first = candidates[0]
                return {
                    'tmdb_id': first['id'],
                    'show_name': first['name'],
                    'confidence': 0.0,
                    'reasoning': 'Fell back to first TMDB candidate due to LLM error.'
                }
            else:
                raise ValueError("No candidates available for fallback")