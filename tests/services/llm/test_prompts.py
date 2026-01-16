"""
Unit tests for LangChain LLM service prompt management.

This module tests the prompt loading and management functionality including:
- Prompt file loading with various scenarios
- Error handling for missing or invalid files
- Prompt template creation and validation
- Caching behavior and cache management
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open

from services.llm.prompts import (
    load_prompt_template,
    create_chat_prompt_template,
    list_available_prompts,
    clear_prompt_cache,
    validate_prompt_file,
    get_prompt_info,
    ensure_prompts_directory,
    PROMPT_DIR
)


class TestPromptLoading:
    """Tests for prompt file loading functionality."""

    def test_load_existing_prompt_template(self):
        """Test loading an existing prompt template."""
        # Test with the system prompt from the split parse_filename prompts
        content = load_prompt_template("system_parse_filename_v1")
        
        assert isinstance(content, str)
        assert len(content) > 0
        # System prompt contains rules, not the filename variable
        assert "Output schema" in content or "CRITICAL RULES" in content

    def test_load_nonexistent_prompt_template(self):
        """Test error handling for nonexistent prompt files."""
        with pytest.raises((FileNotFoundError, IOError)) as exc_info:
            load_prompt_template("nonexistent_prompt")
        
        assert "Prompt file not found" in str(exc_info.value) or "Cannot read prompt file" in str(exc_info.value)
        assert "Available prompts:" in str(exc_info.value)

    def test_prompt_caching_behavior(self):
        """Test that prompt caching works correctly."""
        # Clear cache first
        clear_prompt_cache()
        
        # Load prompt twice
        content1 = load_prompt_template("system_parse_filename_v1", use_cache=True)
        content2 = load_prompt_template("system_parse_filename_v1", use_cache=True)
        
        # Should be identical (from cache)
        assert content1 == content2
        assert content1 is content2  # Same object reference due to caching

    def test_cache_bypass(self):
        """Test that cache can be bypassed when needed."""
        # Load with cache
        content1 = load_prompt_template("system_parse_filename_v1", use_cache=True)
        
        # Load without cache
        content2 = load_prompt_template("system_parse_filename_v1", use_cache=False)
        
        # Content should be the same but objects may be different
        assert content1 == content2

    def test_clear_prompt_cache(self):
        """Test cache clearing functionality."""
        # Load a prompt to populate cache
        load_prompt_template("system_parse_filename_v1", use_cache=True)
        
        # Clear cache
        clear_prompt_cache()
        
        # Cache should be empty (we can't directly test this, but no errors should occur)
        content = load_prompt_template("system_parse_filename_v1", use_cache=True)
        assert isinstance(content, str)

    @patch("builtins.open", mock_open(read_data=""))
    @patch("pathlib.Path.exists", return_value=True)
    def test_empty_prompt_file_warning(self, mock_exists):
        """Test warning for empty prompt files."""
        with patch("services.llm.prompts.logger") as mock_logger:
            content = load_prompt_template("empty_prompt")
            assert content == ""
            mock_logger.warning.assert_called_once()

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_file_read_error(self, mock_exists, mock_open):
        """Test error handling for file read errors."""
        with pytest.raises(IOError) as exc_info:
            load_prompt_template("unreadable_prompt")
        
        assert "Cannot read prompt file" in str(exc_info.value)


class TestChatPromptTemplateCreation:
    """Tests for ChatPromptTemplate creation."""

    def test_create_chat_prompt_template_success(self):
        """Test successful ChatPromptTemplate creation."""
        template = create_chat_prompt_template(
            "select_show_name",
            ["show_name", "candidates"]  # Variables that exist in select_show_name prompt
        )
        
        # Should be a ChatPromptTemplate
        from langchain_core.prompts import ChatPromptTemplate
        assert isinstance(template, ChatPromptTemplate)
        
        # Should have the expected input variables
        expected_vars = {"show_name", "candidates"}
        actual_vars = set(template.input_variables)
        assert expected_vars.issubset(actual_vars)

    def test_create_chat_prompt_template_missing_variables(self):
        """Test warning for missing variables in prompt."""
        with patch("services.llm.prompts.logger") as mock_logger:
            template = create_chat_prompt_template(
                "select_show_name",
                ["show_name", "candidates", "nonexistent_variable"]  # nonexistent_variable doesn't exist in prompt
            )
            
            # Should still create template but log warning
            from langchain_core.prompts import ChatPromptTemplate
            assert isinstance(template, ChatPromptTemplate)
            mock_logger.warning.assert_called_once()

    def test_create_chat_prompt_template_nonexistent_file(self):
        """Test error handling for nonexistent prompt files."""
        with pytest.raises(ValueError) as exc_info:
            create_chat_prompt_template(
                "nonexistent_prompt",
                ["variable1"]
            )
        
        assert "Cannot create prompt template" in str(exc_info.value)


class TestPromptUtilities:
    """Tests for prompt utility functions."""

    def test_list_available_prompts(self):
        """Test listing available prompt files."""
        prompts = list_available_prompts()
        
        assert isinstance(prompts, list)
        # Should include the migrated prompts (parse_filename was split into system/user)
        expected_prompts = [
            "system_parse_filename_v1",
            "user_parse_filename_v1",
            "select_show_name", 
            "suggest_short_dirname",
            "suggest_short_filename"
        ]
        
        for expected in expected_prompts:
            assert expected in prompts

    @patch("pathlib.Path.exists", return_value=False)
    def test_list_available_prompts_no_directory(self, mock_exists):
        """Test listing prompts when directory doesn't exist."""
        with patch("services.llm.prompts.logger") as mock_logger:
            prompts = list_available_prompts()
            assert prompts == []
            mock_logger.warning.assert_called_once()

    def test_validate_prompt_file_valid(self):
        """Test validation of valid prompt file."""
        is_valid = validate_prompt_file("system_parse_filename_v1")
        assert is_valid is True

    def test_validate_prompt_file_invalid(self):
        """Test validation of invalid prompt file."""
        is_valid = validate_prompt_file("nonexistent_prompt")
        assert is_valid is False

    def test_get_prompt_info_existing(self):
        """Test getting information about existing prompt."""
        info = get_prompt_info("user_parse_filename_v1")
        
        assert info is not None
        assert info["name"] == "user_parse_filename_v1"
        assert info["exists"] is True
        assert info["size"] > 0
        assert info["lines"] > 0
        assert isinstance(info["variables"], list)
        assert "filename" in info["variables"]

    def test_get_prompt_info_nonexistent(self):
        """Test getting information about nonexistent prompt."""
        info = get_prompt_info("nonexistent_prompt")
        assert info is None

    def test_ensure_prompts_directory_exists(self):
        """Test ensuring prompts directory exists."""
        # Should succeed since directory already exists
        result = ensure_prompts_directory()
        assert result is True

    @patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied"))
    def test_ensure_prompts_directory_error(self, mock_mkdir):
        """Test error handling when directory creation fails."""
        with patch("services.llm.prompts.logger") as mock_logger:
            result = ensure_prompts_directory()
            assert result is False
            mock_logger.error.assert_called_once()


class TestPromptIntegration:
    """Integration tests for prompt management."""

    def test_end_to_end_prompt_usage(self):
        """Test complete prompt loading and template creation workflow."""
        # Load prompt content
        content = load_prompt_template("select_show_name")
        assert isinstance(content, str)
        assert len(content) > 0
        
        # Create template
        template = create_chat_prompt_template(
            "select_show_name",
            ["show_name", "candidates"]
        )
        
        # Template should be usable
        from langchain_core.prompts import ChatPromptTemplate
        assert isinstance(template, ChatPromptTemplate)
        
        # Should be able to format with variables
        formatted = template.format_messages(
            show_name="Test Show",
            candidates="[]"
        )
        
        assert len(formatted) > 0
        assert "Test Show" in str(formatted[0].content)

    def test_all_migrated_prompts_loadable(self):
        """Test that all migrated prompt files can be loaded."""
        expected_prompts = [
            "system_parse_filename_v1",
            "user_parse_filename_v1",
            "select_show_name",
            "suggest_short_dirname", 
            "suggest_short_filename"
        ]
        
        for prompt_name in expected_prompts:
            content = load_prompt_template(prompt_name)
            assert isinstance(content, str)
            assert len(content) > 0
            
            # Should be able to create template (with minimal variables)
            template = create_chat_prompt_template(prompt_name, ["dummy_var"])
            from langchain_core.prompts import ChatPromptTemplate
            assert isinstance(template, ChatPromptTemplate)