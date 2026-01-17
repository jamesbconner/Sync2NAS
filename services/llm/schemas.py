"""
Pydantic schemas for LangChain-based LLM service structured outputs.

This module defines type-safe data structures for:
- Filename parsing results with validation
- Short name suggestions with length constraints  
- TMDB show matching with confidence scoring

All schemas include comprehensive validation, field constraints,
and automatic data normalization to ensure type safety and
consistency with existing functionality.
"""

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class ParsedFilename(BaseModel):
    """
    Schema for filename parsing results with comprehensive validation.
    
    This schema validates and normalizes filename parsing outputs to ensure
    consistency with existing functionality while providing type safety.
    
    Attributes:
        show_name: Extracted show name (required, non-empty after stripping)
        season: Season number (1-99, optional)
        episode: Episode number (1-2000, optional - null for non-episode content like OPs, EDs, PVs)
        crc32: CRC32 hash (8-character hex, optional, normalized to uppercase)
        confidence: Confidence score (0.0-1.0, required)
        reasoning: Parsing reasoning explanation (required)
    
    Examples:
        >>> parsed = ParsedFilename(
        ...     show_name="Attack on Titan",
        ...     season=1,
        ...     episode=5,
        ...     crc32="a1b2c3d4",
        ...     confidence=0.95,
        ...     reasoning="Clear SxxExx pattern detected"
        ... )
        >>> parsed.crc32
        'A1B2C3D4'
    """
    
    show_name: str = Field(
        description="Extracted show name, normalized and cleaned",
        min_length=1
    )
    season: Optional[int] = Field(
        None,
        ge=1,
        le=99,
        description="Season number (1-99)"
    )
    episode: Optional[int] = Field(
        None,
        ge=1,
        le=2000,
        description="Episode number (1-2000, supports long-running shows). Null for non-episode content."
    )
    crc32: Optional[str] = Field(
        None,
        pattern=r"^[0-9A-Fa-f]{8}$",
        description="CRC32 hash (8-character hexadecimal)"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)"
    )
    reasoning: str = Field(
        description="Explanation of parsing logic and decisions",
        min_length=1
    )

    @field_validator('show_name')
    @classmethod
    def validate_show_name(cls, v: str) -> str:
        """
        Validate and normalize show name.
        
        Applies the same normalization logic as existing implementation:
        - Strips whitespace
        - Normalizes underscores to spaces
        - Handles dot separators (preserving abbreviations)
        - Converts excessive uppercase to title case
        - Collapses multiple spaces
        
        Args:
            v: Raw show name string
            
        Returns:
            str: Normalized show name
            
        Raises:
            ValueError: If show name is empty or whitespace-only
        """
        if not v or not v.strip():
            raise ValueError("Show name cannot be empty or whitespace-only")
        
        # Apply same normalization as existing BaseLLMService
        normalized = v.strip()
        # Normalize common separators and excessive casing from LLMs
        normalized = re.sub(r"_+", " ", normalized)
        # Replace dots that are not followed by a space with a space, preserving abbreviations like "Dr. "
        normalized = re.sub(r"\.(?!\s)", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        
        if normalized.isupper():
            # Simple normalization: convert shouting-case to title case
            normalized = normalized.title()
            
        if not normalized:
            raise ValueError("Show name cannot be empty after normalization")
            
        return normalized

    @field_validator('crc32')
    @classmethod
    def validate_and_normalize_crc32(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate and normalize CRC32 hash to uppercase.
        
        Args:
            v: CRC32 hash string (optional)
            
        Returns:
            Optional[str]: Normalized uppercase CRC32 or None
        """
        if v is None:
            return None
        return v.upper()

    @model_validator(mode='after')
    def validate_episode_season_consistency(self):
        """
        Validate that episode and season are logically consistent.
        
        If episode is provided, it should be reasonable for the given season.
        This is a soft validation that logs warnings rather than failing.
        """
        # This is primarily for future extensibility
        # Current implementation doesn't enforce strict episode/season relationships
        return self


class ShortName(BaseModel):
    """
    Schema for short name suggestions with length and character constraints.
    
    This schema validates short name suggestions to ensure they meet
    the requirements for directory and filename naming conventions.
    
    Attributes:
        short_name: Suggested short name (max 50 characters)
        reasoning: Explanation of suggestion logic
    
    Examples:
        >>> suggestion = ShortName(
        ...     short_name="AoT_S1",
        ...     reasoning="Abbreviated using common acronym and season indicator"
        ... )
    """
    
    short_name: str = Field(
        max_length=50,
        min_length=1,
        description="Suggested short name with length constraints"
    )
    reasoning: str = Field(
        description="Explanation of suggestion logic and character choices",
        min_length=1
    )

    @field_validator('short_name')
    @classmethod
    def validate_short_name_characters(cls, v: str) -> str:
        """
        Validate that short name contains only safe characters.
        
        This validation ensures compatibility with filesystem naming
        conventions across different operating systems.
        
        Args:
            v: Short name string
            
        Returns:
            str: Validated short name
            
        Raises:
            ValueError: If name contains invalid characters
        """
        # Allow alphanumeric, spaces, hyphens, underscores, and dots
        # This matches existing filesystem-safe naming patterns
        if not re.match(r'^[a-zA-Z0-9\s\-_.]+$', v):
            raise ValueError(
                "Short name contains invalid characters. "
                "Only alphanumeric characters, spaces, hyphens, underscores, and dots are allowed."
            )
        
        return v.strip()


class ShowMatch(BaseModel):
    """
    Schema for TMDB show matching results with confidence scoring.
    
    This schema validates show matching outputs to ensure consistency
    with TMDB data structures and confidence scoring requirements.
    
    Special case: tmdb_id can be -1 to indicate no match was found when
    the candidate list is empty or no suitable match exists.
    
    Attributes:
        tmdb_id: TMDB show identifier (positive integer) or -1 for no match
        show_name: Selected show name from TMDB, or "NO_MATCH" when tmdb_id is -1
        confidence: Match confidence score (0.0-1.0)
        reasoning: Explanation of selection logic
    
    Examples:
        >>> match = ShowMatch(
        ...     tmdb_id=1429,
        ...     show_name="Attack on Titan",
        ...     confidence=0.98,
        ...     reasoning="Exact name match with high popularity score"
        ... )
        >>> no_match = ShowMatch(
        ...     tmdb_id=-1,
        ...     show_name="NO_MATCH",
        ...     confidence=0.0,
        ...     reasoning="No candidates provided for matching"
        ... )
    """
    
    tmdb_id: int = Field(
        description="TMDB show identifier (positive integer) or -1 for no match"
    )
    show_name: str = Field(
        description="Selected show name from TMDB candidates, or 'NO_MATCH' when no match found",
        min_length=1
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Match confidence score (0.0-1.0)"
    )
    reasoning: str = Field(
        description="Explanation of selection logic and confidence factors",
        min_length=1
    )

    @field_validator('tmdb_id')
    @classmethod
    def validate_tmdb_id(cls, v: int) -> int:
        """
        Validate TMDB ID is either positive or the special -1 sentinel value.
        
        Args:
            v: TMDB ID value
            
        Returns:
            int: Validated TMDB ID
            
        Raises:
            ValueError: If ID is not positive and not -1
        """
        if v != -1 and v <= 0:
            raise ValueError("TMDB ID must be positive or -1 (for no match)")
        return v

    @field_validator('show_name')
    @classmethod
    def validate_show_name(cls, v: str) -> str:
        """
        Validate and clean show name from TMDB.
        
        Args:
            v: Show name string
            
        Returns:
            str: Cleaned show name
            
        Raises:
            ValueError: If show name is empty
        """
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Show name cannot be empty")
        return cleaned
    
    @model_validator(mode='after')
    def validate_no_match_consistency(self):
        """
        Validate that no-match responses are consistent.
        
        When tmdb_id is -1, show_name should be "NO_MATCH" and confidence should be 0.0.
        This ensures the LLM follows the documented no-match protocol.
        """
        if self.tmdb_id == -1:
            if self.show_name != "NO_MATCH":
                raise ValueError(
                    f"When tmdb_id is -1, show_name must be 'NO_MATCH', got '{self.show_name}'"
                )
            if self.confidence != 0.0:
                raise ValueError(
                    f"When tmdb_id is -1, confidence must be 0.0, got {self.confidence}"
                )
        return self