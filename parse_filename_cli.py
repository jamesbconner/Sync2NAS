import argparse
import logging
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

try:
    from ollama import Client
except Exception as import_error:  # pragma: no cover
    raise SystemExit(
        "The 'ollama' package is required. Install with: pip install ollama"
    ) from import_error

try:
    from pydantic import BaseModel, Field, ValidationError, field_validator
except Exception as import_error:  # pragma: no cover
    raise SystemExit(
        "The 'pydantic' package is required. Install with: pip install -r requirements.txt"
    ) from import_error


class ParsedFilename(BaseModel):
    show_name: str = Field(min_length=1)
    season: int | None = None
    episode: int  # required and must not be null
    hash: str | None = None
    confidence: float
    reasoning: str = Field(min_length=1)

    @field_validator("confidence")
    @classmethod
    def validate_confidence_bounds(cls, value: float) -> float:
        if not (0.0 <= float(value) <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive")
        return float(value)

    @field_validator("hash", mode="before")
    @classmethod
    def validate_hash(cls, value: Any) -> Any:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            raise ValueError("boolean is not a valid hash value")
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed.isdigit():
                return str(int(trimmed))
        return value

    @field_validator("season", mode="before")
    @classmethod
    def coerce_integer_or_none(cls, value: Any) -> Any:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            raise ValueError("boolean is not a valid integer value")
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed.isdigit():
                return int(trimmed)
        return value

    @field_validator("episode", mode="before")
    @classmethod
    def coerce_required_integer(cls, value: Any) -> int:
        if value is None or value == "":
            raise ValueError("episode is required and cannot be null")
        if isinstance(value, bool):
            raise ValueError("boolean is not a valid integer value")
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed.isdigit():
                return int(trimmed)
        raise ValueError("episode must be an integer")


def load_prompt_template(template_path: Path) -> str:
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def build_prompt(template: str, filename_text: str) -> str:
    # Avoid str.format because the template contains literal braces (e.g., regex {8})
    # that would be interpreted as format fields. Perform a simple placeholder replace.
    return template.format(filename=filename_text)
    #return template.replace("{filename}", filename_text)


def call_ollama(
    host: str,
    model: str,
    prompt: str,
    temperature: float,
    json_schema: Dict[str, Any] | None,
) -> str:
    client = Client(host=host)
    # Build request; only pass 'format' when a schema is provided. Some models
    # (e.g., certain gpt-oss variants) return empty output when 'format' is set.
    request_kwargs: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "options": {"temperature": temperature},
    }
    if json_schema is not None:
        request_kwargs["format"] = json_schema

    response: Dict[str, Any] = client.generate(**request_kwargs)
    text = (response.get("response") or "").strip()

    # Fallback: if no text and we passed a format/schema, retry without it
    if not text and "format" in request_kwargs:
        request_kwargs.pop("format", None)
        response = client.generate(**request_kwargs)
        text = (response.get("response") or "").strip()

    if not text:
        error_message = response.get("error") or "empty response from model"
        raise SystemExit(f"Ollama returned no text for model '{model}': {error_message}")

    return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Parse a filename string into structured JSON using an Ollama model "
            "and the prompt at prompts/parse_filename.txt."
        )
    )
    parser.add_argument(
        "filename",
        nargs="?",
        help="The raw filename or title string to parse",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Path to a text file with one input string per line",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", "gpt-oss:20b"),
        help="Ollama model name (default: gpt-oss:20b or $OLLAMA_MODEL)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        help="Ollama host URL (default: http://localhost:11434 or $OLLAMA_HOST)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=float(os.environ.get("OLLAMA_TEMPERATURE", 0.2)),
        help="Sampling temperature (default: 0.2 or $OLLAMA_TEMPERATURE)",
    )
    parser.add_argument(
        "--no-schema",
        action="store_true",
        help=(
            "Disable structured outputs. When set, uses format=\"json\" rather than "
            "passing the Pydantic JSON Schema to Ollama."
        ),
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print the raw model output (no JSON pretty-print)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable INFO logging (logs are written to stderr)",
    )
    args = parser.parse_args()
    if not args.filename and not args.file:
        parser.error("You must provide either a positional filename string or --file path")
    return args


def main() -> None:
    args = parse_args()

    # Configure an application-specific logger to avoid enabling 3rd-party INFO logs
    logger = logging.getLogger("parse_filename_cli")
    logger.setLevel(logging.INFO if args.verbose else logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO if args.verbose else logging.WARNING)
    stream_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.handlers.clear()
    logger.addHandler(stream_handler)
    logger.propagate = False

    # Silence noisy HTTP client libraries regardless of verbosity
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Resolve prompt path relative to this script's directory
    repo_root = Path(__file__).resolve().parent
    prompt_path = repo_root / "prompts" / "parse_filename.txt"

    template = load_prompt_template(prompt_path)
    schema_to_use: Dict[str, Any] | None = None if args.no_schema else ParsedFilename.model_json_schema()

    def process_one(input_text: str) -> None:
        logger.info("Parsing filename: %s", input_text)
        prompt_local = build_prompt(template, input_text)
        model_output_local = call_ollama(
            host=args.host,
            model=args.model,
            prompt=prompt_local,
            temperature=args.temperature,
            json_schema=schema_to_use,
        )
        if args.raw:
            print(model_output_local)
            return
        try:
            parsed_local = ParsedFilename.model_validate_json(model_output_local)
            print(json.dumps(parsed_local.model_dump(), indent=2, ensure_ascii=False))
        except Exception as err:
            # Echo the model output, then write the error to stderr and continue
            print(model_output_local)
            print(f"Error: Model output failed JSON or schema validation: {err}", file=sys.stderr)

    if args.file:
        try:
            for raw_line in args.file.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                process_one(line)
        except FileNotFoundError:
            raise SystemExit(f"Input file not found: {args.file}")
    else:
        process_one(args.filename)


if __name__ == "__main__":
    main()
