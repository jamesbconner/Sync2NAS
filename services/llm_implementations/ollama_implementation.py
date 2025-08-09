import logging
import json
import re
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any, List
from ollama import Client
from utils.sync2nas_config import load_configuration
from services.llm_implementations.base_llm_service import BaseLLMService

logger = logging.getLogger(__name__)

class ParsedFilename(BaseModel):
    show_name: str = Field(..., description="Full show name, as extracted from filename")
    season: int | None = Field(..., description="Season number as integer, or null if not present")
    episode: int = Field(..., description="Episode number as integer, or null if not present")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence between 0.0 and 1.0")
    reasoning: str = Field(..., description="Explanation of field choices and confidence")

class SuggestedShowName(BaseModel):
    tmdb_id: int = Field(..., description="TMDB ID of the show")
    show_name: str = Field(..., description="Full show name, as extracted from filename")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence between 0.0 and 1.0")
    reasoning: str = Field(..., description="Explanation of field choices and confidence")

class OllamaLLMService(BaseLLMService):
    """
    LLM service implementation using a local Ollama server and model.

    Provides filename parsing, directory/filename suggestion, and show name selection using LLM.

    Attributes:
        config (dict): Configuration object.
        model (str): Model name used by Ollama.
        client (Client): Ollama client instance.
    """
    def __init__(self, config):
        """
        Initialize the Ollama LLM service.
        Args:
            config: Loaded configuration object
        """
        self.config = config
        self.model = self.config.get('ollama', 'model', fallback='llama3.2')
        self.client = Client()
        logger.info(f"Ollama LLM service initialized with model: {self.model}")

    def parse_filename(self, filename: str, max_tokens: int = 150) -> Dict[str, Any]:
        """
        Parse a filename using Ollama LLM to extract show metadata.
        Args:
            filename: Raw filename to parse
            max_tokens: Maximum tokens for LLM response
        Returns:
            dict: Parsed metadata
        """
        logger.info(f"Parsing filename with Ollama LLM: {filename}")
        cleaned_filename = self._clean_filename_for_llm(filename)
        prompt = self.load_prompt('parse_filename').format(filename=cleaned_filename)
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                format=ParsedFilename.model_json_schema(),
                options={"num_predict": max_tokens, "temperature": 0.0}
            )

            # Extract the JSON string from the response object
            if hasattr(response, 'response'):
                content = response.response
            elif isinstance(response, dict) and 'response' in response:
                content = response['response']
            else:
                content = response  # fallback

            if not isinstance(content, str) or not content.strip():
                logger.error("Empty Ollama response; using fallback parser")
                return self._fallback_parse(filename)

            logger.debug(f"Ollama response: {content}")

            # Extract first JSON object in case of extra prose or code fences
            json_text = self._extract_first_json_object(content)
            if json_text is None:
                logger.error("No JSON object found in Ollama response; using fallback parser")
                return self._fallback_parse(filename)

            try:
                result = json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from Ollama response: {e}")
                return self._fallback_parse(filename)

            # Strong validation against the Pydantic model to ensure structure/types
            try:
                model_instance = ParsedFilename.model_validate(result)
                validated_dict = model_instance.model_dump()
            except ValidationError as e:
                logger.error(f"Pydantic validation failed for Ollama response: {e}")
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

        match = re.search(r"\{[\s\S]*\}", stripped)
        return match.group(0) if match else None

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
        prompt = self.load_prompt('suggest_short_dirname')
        prompt = prompt.format(max_length=max_length, long_name=long_name)
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={"num_predict": max_length, "temperature": 0.1}
            )
            if hasattr(response, 'response'):
                content = response.response.strip()
            elif isinstance(response, dict) and 'response' in response:
                content = response['response'].strip()
            else:
                content = str(response).strip()
            # Only keep the first line and truncate if needed
            short_name = content.splitlines()[0][:max_length]
            # Remove problematic characters
            short_name = re.sub(r'[^\w\- ]', '', short_name)
            logger.debug(f"LLM recommended: {short_name}")
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.exception(f"LLM error: {e}.")
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
        prompt = self.load_prompt('suggest_short_filename')
        prompt = prompt.format(max_length=max_length, long_name=long_name)
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={"num_predict": max_length, "temperature": 0.1}
            )
            if hasattr(response, 'response'):
                content = response.response.strip()
            elif isinstance(response, dict) and 'response' in response:
                content = response['response'].strip()
            else:
                content = str(response).strip()
            short_name = content.splitlines()[0][:max_length]
            short_name = re.sub(r'[^\w\-. ]', '', short_name)
            logger.debug(f"LLM recommended: {short_name}")
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.exception(f"LLM error: {e}.")
            return long_name[:max_length]

    def suggest_show_name(self, show_name: str, detailed_results: list) -> dict:
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
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                format=SuggestedShowName.model_json_schema(),
                options={"num_predict": 256, "temperature": 0.1}
            )
            content = response.response if hasattr(response, 'response') else response
            result = json.loads(content)
            
            logger.debug(f"LLM response: {content}")

            # Check if the result has the required fields
            if 'tmdb_id' in result and 'show_name' in result:
                return result
            else:
                logger.warning(f"LLM response missing required fields: {result}")
                # Fall back to first candidate if required fields are missing
                if candidates:
                    first = candidates[0]
                    return {'tmdb_id': first['id'], 'show_name': first['name']}
                else:
                    raise ValueError("No candidates available for fallback")
        except Exception as e:
            logger.exception(f"LLM error: {e}")
            # Fall back to first candidate on any error
            if candidates:
                first = candidates[0]
                return {'tmdb_id': first['id'], 'show_name': first['name']}
            else:
                raise ValueError("No candidates available for fallback") 