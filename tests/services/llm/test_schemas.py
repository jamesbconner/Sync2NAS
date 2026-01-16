"""
Property-based tests for LangChain LLM service Pydantic schemas.

This module tests the validation and normalization behavior of:
- ParsedFilename schema with comprehensive field validation
- ShortName schema with character and length constraints
- ShowMatch schema with TMDB data validation

Uses Hypothesis for property-based testing to ensure schemas handle
all valid inputs correctly and reject invalid inputs appropriately.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from pydantic import ValidationError

from services.llm.schemas import ParsedFilename, ShortName, ShowMatch


class TestParsedFilenameSchema:
    """Property-based tests for ParsedFilename schema validation."""

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(
        show_name=st.text(min_size=1, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))).filter(lambda x: x.strip() and len(x.strip()) > 0 and not x.strip().replace('.', '').replace('_', '').replace(' ', '') == ''),
        season=st.one_of(st.none(), st.integers(min_value=1, max_value=99)),
        episode=st.one_of(st.none(), st.integers(min_value=1, max_value=2000)),
        crc32=st.one_of(
            st.none(),
            st.text(min_size=8, max_size=8, alphabet="0123456789ABCDEFabcdef")
        ),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        reasoning=st.text(min_size=1)
    )
    def test_valid_parsed_filename_creation(self, show_name, season, episode, crc32, confidence, reasoning):
        """
        Test that ParsedFilename schema validates and normalizes data correctly.
        
        For any valid filename parsing data within specified ranges and formats,
        the ParsedFilename schema should validate correctly and normalize fields appropriately.
        """
        # Create ParsedFilename with valid data
        parsed = ParsedFilename(
            show_name=show_name,
            season=season,
            episode=episode,
            crc32=crc32,
            confidence=confidence,
            reasoning=reasoning
        )
        
        # Verify all fields are properly set and normalized
        assert parsed.show_name.strip() == parsed.show_name  # Should be stripped
        assert len(parsed.show_name) > 0  # Should not be empty
        
        if season is not None:
            assert 1 <= parsed.season <= 99
        else:
            assert parsed.season is None
            
        if episode is not None:
            assert 1 <= parsed.episode <= 2000
        else:
            assert parsed.episode is None
            
        if crc32 is not None:
            assert len(parsed.crc32) == 8
            assert parsed.crc32 == parsed.crc32.upper()  # Should be normalized to uppercase
            assert all(c in "0123456789ABCDEF" for c in parsed.crc32)
        else:
            assert parsed.crc32 is None
            
        assert 0.0 <= parsed.confidence <= 1.0
        assert len(parsed.reasoning) > 0

    @given(
        show_name=st.one_of(
            st.just(""),  # Empty string
            st.just("   "),  # Whitespace only
            st.just("\t\n"),  # Other whitespace
        )
    )
    def test_invalid_show_name_rejection(self, show_name):
        """Test that empty or whitespace-only show names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ParsedFilename(
                show_name=show_name,
                season=1,
                episode=1,
                crc32=None,
                confidence=0.5,
                reasoning="Test reasoning"
            )
        
        # Verify the error is about show_name validation
        errors = exc_info.value.errors()
        assert any("show_name" in str(error) for error in errors)

    @given(
        season=st.one_of(
            st.integers(max_value=0),  # Too low
            st.integers(min_value=100)  # Too high
        )
    )
    def test_invalid_season_range_rejection(self, season):
        """Test that seasons outside 1-99 range are rejected."""
        with pytest.raises(ValidationError):
            ParsedFilename(
                show_name="Test Show",
                season=season,
                episode=1,
                crc32=None,
                confidence=0.5,
                reasoning="Test reasoning"
            )

    @given(
        episode=st.one_of(
            st.integers(max_value=0),  # Too low
            st.integers(min_value=2001)  # Too high
        )
    )
    def test_invalid_episode_range_rejection(self, episode):
        """Test that episodes outside 1-2000 range are rejected."""
        with pytest.raises(ValidationError):
            ParsedFilename(
                show_name="Test Show",
                season=1,
                episode=episode,
                crc32=None,
                confidence=0.5,
                reasoning="Test reasoning"
            )

    @given(
        crc32=st.one_of(
            st.text(min_size=1, max_size=7),  # Too short
            st.text(min_size=9),  # Too long
            st.text(min_size=8, max_size=8, alphabet="GHIJKLMNOP"),  # Invalid chars
        )
    )
    def test_invalid_crc32_format_rejection(self, crc32):
        """Test that invalid CRC32 formats are rejected."""
        assume(len(crc32) != 8 or not all(c in "0123456789ABCDEFabcdef" for c in crc32))
        
        with pytest.raises(ValidationError):
            ParsedFilename(
                show_name="Test Show",
                season=1,
                episode=1,
                crc32=crc32,
                confidence=0.5,
                reasoning="Test reasoning"
            )

    @given(
        confidence=st.one_of(
            st.floats(max_value=-0.1),  # Below 0.0
            st.floats(min_value=1.1),  # Above 1.0
            st.just(float('nan')),  # NaN
            st.just(float('inf')),  # Infinity
            st.just(float('-inf'))  # Negative infinity
        )
    )
    def test_invalid_confidence_range_rejection(self, confidence):
        """Test that confidence scores outside 0.0-1.0 range are rejected."""
        with pytest.raises(ValidationError):
            ParsedFilename(
                show_name="Test Show",
                season=1,
                episode=1,
                crc32=None,
                confidence=confidence,
                reasoning="Test reasoning"
            )

    def test_show_name_normalization_examples(self):
        """Test specific show name normalization cases from existing implementation."""
        test_cases = [
            ("ATTACK_ON_TITAN", "Attack On Titan"),  # Uppercase with underscores
            ("attack.on.titan", "attack on titan"),  # Dots to spaces
            ("Dr. Stone", "Dr. Stone"),  # Preserve abbreviations
            ("show__name", "show name"),  # Multiple underscores
            ("  spaced  name  ", "spaced name"),  # Extra whitespace
        ]
        
        for input_name, expected_output in test_cases:
            parsed = ParsedFilename(
                show_name=input_name,
                season=1,
                episode=1,
                crc32=None,
                confidence=0.5,
                reasoning="Test normalization"
            )
            assert parsed.show_name == expected_output

    def test_crc32_normalization_to_uppercase(self):
        """Test that CRC32 values are normalized to uppercase."""
        test_cases = ["a1b2c3d4", "A1B2C3D4", "1a2B3c4D"]
        
        for crc32_input in test_cases:
            parsed = ParsedFilename(
                show_name="Test Show",
                season=1,
                episode=1,
                crc32=crc32_input,
                confidence=0.5,
                reasoning="Test CRC32 normalization"
            )
            assert parsed.crc32 == crc32_input.upper()

    @given(
        crc32=st.text(min_size=8, max_size=8, alphabet="0123456789ABCDEFabcdef")
    )
    def test_crc32_validation_and_normalization_property(self, crc32):
        """
        Test that CRC32 validation accepts valid hex strings and normalizes to uppercase.
        
        For any valid 8-character hexadecimal string provided as CRC32,
        the validation should accept it and normalize it to uppercase format consistently.
        """
        parsed = ParsedFilename(
            show_name="Test Show",
            season=1,
            episode=1,
            crc32=crc32,
            confidence=0.5,
            reasoning="Test CRC32 property validation"
        )
        
        # Verify CRC32 is normalized to uppercase
        assert parsed.crc32 == crc32.upper()
        assert len(parsed.crc32) == 8
        assert all(c in "0123456789ABCDEF" for c in parsed.crc32)
        
        # Verify it's a valid hexadecimal string
        int(parsed.crc32, 16)  # Should not raise ValueError


class TestShortNameSchema:
    """Property-based tests for ShortName schema validation."""

    @given(
        short_name=st.text(
            min_size=1,
            max_size=50,
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_."
        ),
        reasoning=st.text(min_size=1)
    )
    def test_valid_short_name_creation(self, short_name, reasoning):
        """Test that valid short names are accepted and normalized."""
        assume(short_name.strip())  # Ensure not just whitespace
        
        suggestion = ShortName(
            short_name=short_name,
            reasoning=reasoning
        )
        
        assert len(suggestion.short_name) <= 50
        assert len(suggestion.short_name) > 0
        assert suggestion.short_name == suggestion.short_name.strip()
        assert len(suggestion.reasoning) > 0

    @given(
        short_name=st.text(min_size=51)  # Too long
    )
    def test_invalid_short_name_length_rejection(self, short_name):
        """Test that short names exceeding 50 characters are rejected."""
        with pytest.raises(ValidationError):
            ShortName(
                short_name=short_name,
                reasoning="Test reasoning"
            )

    def test_invalid_characters_rejection(self):
        """Test that short names with invalid characters are rejected."""
        invalid_names = [
            "name/with/slashes",
            "name\\with\\backslashes", 
            "name:with:colons",
            "name*with*asterisks",
            "name?with?questions",
            "name<with>brackets",
            "name|with|pipes"
        ]
        
        for invalid_name in invalid_names:
            with pytest.raises(ValidationError):
                ShortName(
                    short_name=invalid_name,
                    reasoning="Test invalid characters"
                )


class TestShowMatchSchema:
    """Property-based tests for ShowMatch schema validation."""

    @given(
        tmdb_id=st.integers(min_value=1, max_value=1000000),
        show_name=st.text(min_size=1).filter(lambda x: x.strip()),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        reasoning=st.text(min_size=1)
    )
    def test_valid_show_match_creation(self, tmdb_id, show_name, confidence, reasoning):
        """Test that valid show matches are accepted and normalized."""
        match = ShowMatch(
            tmdb_id=tmdb_id,
            show_name=show_name,
            confidence=confidence,
            reasoning=reasoning
        )
        
        assert match.tmdb_id > 0
        assert len(match.show_name.strip()) > 0
        assert match.show_name == match.show_name.strip()
        assert 0.0 <= match.confidence <= 1.0
        assert len(match.reasoning) > 0

    @given(
        tmdb_id=st.integers(max_value=0)  # Invalid ID
    )
    def test_invalid_tmdb_id_rejection(self, tmdb_id):
        """Test that non-positive TMDB IDs are rejected."""
        with pytest.raises(ValidationError):
            ShowMatch(
                tmdb_id=tmdb_id,
                show_name="Test Show",
                confidence=0.5,
                reasoning="Test reasoning"
            )

    @given(
        show_name=st.one_of(
            st.just(""),  # Empty string
            st.just("   "),  # Whitespace only
        )
    )
    def test_invalid_show_name_rejection(self, show_name):
        """Test that empty or whitespace-only show names are rejected."""
        with pytest.raises(ValidationError):
            ShowMatch(
                tmdb_id=1429,
                show_name=show_name,
                confidence=0.5,
                reasoning="Test reasoning"
            )