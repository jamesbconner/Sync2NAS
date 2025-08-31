"""Data models for configuration validation results and errors."""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class ErrorCode(Enum):
    """Error codes for configuration validation issues."""
    MISSING_SECTION = "missing_section"
    MISSING_KEY = "missing_key"
    INVALID_VALUE = "invalid_value"
    INVALID_SERVICE = "invalid_service"
    API_KEY_INVALID = "api_key_invalid"
    SERVICE_UNREACHABLE = "service_unreachable"
    CONNECTIVITY_FAILED = "connectivity_failed"
    AUTHENTICATION_FAILED = "authentication_failed"
    MODEL_UNAVAILABLE = "model_unavailable"


@dataclass
class ValidationError:
    """Represents a configuration validation error."""
    section: str
    key: Optional[str]
    message: str
    suggestion: Optional[str]
    error_code: ErrorCode
    
    def __str__(self) -> str:
        """Return formatted error message."""
        location = f"[{self.section}]"
        if self.key:
            location += f".{self.key}"
        
        result = f"{location}: {self.message}"
        if self.suggestion:
            result += f"\n  Suggestion: {self.suggestion}"
        return result


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]
    suggestions: List[str]
    
    def __post_init__(self):
        """Ensure is_valid reflects the presence of errors."""
        self.is_valid = len(self.errors) == 0
    
    def add_error(self, error: ValidationError) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(warning)
    
    def add_suggestion(self, suggestion: str) -> None:
        """Add a suggestion to the validation result."""
        self.suggestions.append(suggestion)
    
    def merge(self, other: 'ValidationResult') -> None:
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.suggestions.extend(other.suggestions)
        self.is_valid = len(self.errors) == 0


@dataclass
class HealthCheckResult:
    """Result of a configuration health check."""
    service: str
    is_healthy: bool
    response_time_ms: Optional[float]
    error_message: Optional[str]
    details: dict
    
    def __str__(self) -> str:
        """Return formatted health check result."""
        status = "✓ Healthy" if self.is_healthy else "✗ Unhealthy"
        result = f"{self.service}: {status}"
        
        if self.response_time_ms is not None:
            result += f" ({self.response_time_ms:.1f}ms)"
        
        if self.error_message:
            result += f"\n  Error: {self.error_message}"
        
        return result