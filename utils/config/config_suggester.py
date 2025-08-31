"""Configuration error suggestion system for intelligent error recovery."""

import difflib
from typing import Dict, List, Optional, Set, Any, Tuple
from .validation_models import ValidationError, ErrorCode


class ConfigSuggester:
    """Provides intelligent suggestions for configuration errors and typos."""
    
    # Known section names and their common variations
    SECTION_NAMES = {
        'llm': ['LLM', 'Llm'],
        'openai': ['OpenAI', 'OPENAI', 'Openai', 'openAI'],
        'anthropic': ['Anthropic', 'ANTHROPIC', 'anthropic', 'Claude'],
        'ollama': ['Ollama', 'OLLAMA', 'ollama'],
        'sftp': ['SFTP', 'Sftp', 'ftp', 'FTP'],
        'tmdb': ['TMDB', 'Tmdb', 'themoviedb', 'TheMovieDB'],
        'database': ['Database', 'DATABASE', 'db', 'DB'],
        'transfers': ['Transfers', 'TRANSFERS', 'transfer', 'Transfer'],
        'routing': ['Routing', 'ROUTING', 'routes', 'Routes']
    }
    
    # Known configuration keys and their common variations
    CONFIG_KEYS = {
        'api_key': ['apikey', 'api-key', 'key', 'token', 'auth_key', 'auth_token'],
        'model': ['model_name', 'model-name', 'llm_model', 'ai_model'],
        'service': ['provider', 'backend', 'engine', 'type'],
        'host': ['hostname', 'server', 'url', 'endpoint', 'address'],
        'port': ['port_number', 'port-number'],
        'username': ['user', 'login', 'account'],
        'password': ['pass', 'pwd', 'secret'],
        'timeout': ['time_out', 'time-out', 'wait_time'],
        'max_tokens': ['max-tokens', 'maxTokens', 'token_limit', 'max_length'],
        'temperature': ['temp', 'randomness', 'creativity']
    }
    
    # Common configuration mistakes and their corrections
    COMMON_MISTAKES = {
        # Section name mistakes
        'openai_api_key': ('openai', 'api_key'),
        'anthropic_api_key': ('anthropic', 'api_key'),
        'ollama_model': ('ollama', 'model'),
        'llm_service': ('llm', 'service'),
        
        # Value mistakes
        'gpt4': 'gpt-4',
        'gpt35': 'gpt-3.5-turbo',
        'claude3': 'claude-3-sonnet-20240229',
        'localhost': 'http://localhost:11434',
    }
    
    # Configuration templates for missing sections
    SECTION_TEMPLATES = {
        'llm': {
            'service': 'ollama  # Options: openai, anthropic, ollama'
        },
        'openai': {
            'api_key': 'your_openai_api_key_here',
            'model': 'gpt-4',
            'max_tokens': '4000',
            'temperature': '0.1'
        },
        'anthropic': {
            'api_key': 'your_anthropic_api_key_here',
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': '4000',
            'temperature': '0.1'
        },
        'ollama': {
            'model': 'llama2:7b',
            'host': 'http://localhost:11434',
            'timeout': '30'
        }
    }
    
    def __init__(self):
        """Initialize the configuration suggester."""
        # Build reverse lookup maps for faster searching
        self._section_lookup = {}
        for correct, variations in self.SECTION_NAMES.items():
            for variation in variations + [correct]:
                self._section_lookup[variation.lower()] = correct
        
        self._key_lookup = {}
        for correct, variations in self.CONFIG_KEYS.items():
            for variation in variations + [correct]:
                self._key_lookup[variation.lower()] = correct
    
    def suggest_section_name(self, invalid_name: str) -> Optional[str]:
        """
        Suggest correct section name for typos using fuzzy matching.
        
        Args:
            invalid_name: The invalid section name
            
        Returns:
            Suggested correct section name or None if no good match
        """
        if not invalid_name:
            return None
        
        # Direct lookup for known variations
        normalized = invalid_name.lower()
        if normalized in self._section_lookup:
            return self._section_lookup[normalized]
        
        # Fuzzy matching for typos
        all_sections = list(self.SECTION_NAMES.keys())
        matches = difflib.get_close_matches(
            invalid_name.lower(), 
            all_sections, 
            n=1, 
            cutoff=0.6
        )
        
        if matches:
            return matches[0]
        
        # Check against all variations with lower cutoff
        all_variations = []
        for section, variations in self.SECTION_NAMES.items():
            all_variations.extend([(v.lower(), section) for v in variations + [section]])
        
        variation_names = [v[0] for v in all_variations]
        matches = difflib.get_close_matches(
            invalid_name.lower(),
            variation_names,
            n=1,
            cutoff=0.5
        )
        
        if matches:
            # Find the correct section for this variation
            for variation, section in all_variations:
                if variation == matches[0]:
                    return section
        
        return None
    
    def suggest_config_key(self, section: str, invalid_key: str) -> Optional[str]:
        """
        Suggest correct configuration key for typos.
        
        Args:
            section: Configuration section name
            invalid_key: The invalid key name
            
        Returns:
            Suggested correct key name or None if no good match
        """
        if not invalid_key:
            return None
        
        # Direct lookup for known variations
        normalized = invalid_key.lower()
        if normalized in self._key_lookup:
            return self._key_lookup[normalized]
        
        # Get valid keys for this section
        valid_keys = self._get_valid_keys_for_section(section)
        
        # Fuzzy matching
        matches = difflib.get_close_matches(
            invalid_key.lower(),
            [k.lower() for k in valid_keys],
            n=1,
            cutoff=0.6
        )
        
        if matches:
            # Return the original case version
            for key in valid_keys:
                if key.lower() == matches[0]:
                    return key
        
        return None
    
    def suggest_missing_config(self, service: str) -> List[str]:
        """
        Suggest configuration additions for a service.
        
        Args:
            service: LLM service name (openai, anthropic, ollama)
            
        Returns:
            List of configuration suggestions
        """
        suggestions = []
        
        if service not in self.SECTION_TEMPLATES:
            return suggestions
        
        template = self.SECTION_TEMPLATES[service]
        suggestions.append(f"Add [{service}] section with:")
        
        for key, value in template.items():
            suggestions.append(f"  {key} = {value}")
        
        # Add service-specific guidance
        if service == 'openai':
            suggestions.append("")
            suggestions.append("Get your OpenAI API key from: https://platform.openai.com/api-keys")
        elif service == 'anthropic':
            suggestions.append("")
            suggestions.append("Get your Anthropic API key from: https://console.anthropic.com/")
        elif service == 'ollama':
            suggestions.append("")
            suggestions.append("Install Ollama from: https://ollama.ai/")
            suggestions.append("Pull a model: ollama pull llama2:7b")
        
        return suggestions
    
    def suggest_env_vars(self, section: str, key: str) -> str:
        """
        Suggest environment variable alternative for configuration.
        
        Args:
            section: Configuration section name
            key: Configuration key name
            
        Returns:
            Environment variable suggestion
        """
        env_var = f"SYNC2NAS_{section.upper()}_{key.upper()}"
        return f"Set environment variable: {env_var}=your_value"
    
    def suggest_value_correction(self, section: str, key: str, invalid_value: str) -> Optional[str]:
        """
        Suggest correction for invalid configuration values.
        
        Args:
            section: Configuration section name
            key: Configuration key name
            invalid_value: The invalid value
            
        Returns:
            Suggested correct value or None
        """
        if not invalid_value:
            return None
        
        # Check common mistakes
        normalized_value = invalid_value.lower().strip()
        if normalized_value in self.COMMON_MISTAKES:
            return self.COMMON_MISTAKES[normalized_value]
        
        # Service-specific value suggestions
        if section == 'openai' and key == 'model':
            return self._suggest_openai_model(invalid_value)
        elif section == 'anthropic' and key == 'model':
            return self._suggest_anthropic_model(invalid_value)
        elif section == 'ollama' and key == 'model':
            return self._suggest_ollama_model(invalid_value)
        elif section == 'ollama' and key == 'host':
            return self._suggest_ollama_host(invalid_value)
        elif key == 'service':
            return self._suggest_service_name(invalid_value)
        
        return None
    
    def generate_config_template(self, service: str) -> str:
        """
        Generate a complete configuration template for a service.
        
        Args:
            service: LLM service name
            
        Returns:
            Complete configuration template as string
        """
        lines = []
        
        # Add LLM section if not present
        lines.append("[llm]")
        lines.append(f"service = {service}")
        lines.append("")
        
        # Add service-specific section
        if service in self.SECTION_TEMPLATES:
            lines.append(f"[{service}]")
            template = self.SECTION_TEMPLATES[service]
            
            for key, value in template.items():
                lines.append(f"{key} = {value}")
            
            lines.append("")
        
        # Add helpful comments
        if service == 'openai':
            lines.append("# Get your API key from: https://platform.openai.com/api-keys")
            lines.append("# Available models: gpt-4, gpt-3.5-turbo")
        elif service == 'anthropic':
            lines.append("# Get your API key from: https://console.anthropic.com/")
            lines.append("# Available models: claude-3-sonnet-20240229, claude-3-haiku-20240307")
        elif service == 'ollama':
            lines.append("# Install Ollama: https://ollama.ai/")
            lines.append("# Pull models: ollama pull llama2:7b")
            lines.append("# List models: ollama list")
        
        return "\n".join(lines)
    
    def analyze_configuration_errors(self, config: Dict[str, Any], errors: List[ValidationError]) -> List[str]:
        """
        Analyze configuration errors and provide comprehensive suggestions.
        
        Args:
            config: Current configuration dictionary
            errors: List of validation errors
            
        Returns:
            List of actionable suggestions
        """
        suggestions = []
        
        # Group errors by type
        missing_sections = []
        missing_keys = []
        invalid_values = []
        typos = []
        
        for error in errors:
            if error.error_code == ErrorCode.MISSING_SECTION:
                missing_sections.append(error.section)
            elif error.error_code == ErrorCode.MISSING_KEY:
                missing_keys.append((error.section, error.key))
            elif error.error_code in [ErrorCode.INVALID_VALUE, ErrorCode.INVALID_SERVICE]:
                invalid_values.append(error)
            else:
                typos.append(error)
        
        # Suggest fixes for missing sections
        if missing_sections:
            suggestions.append("Missing configuration sections:")
            for section in missing_sections:
                template_lines = self.suggest_missing_config(section)
                suggestions.extend(f"  {line}" for line in template_lines)
            suggestions.append("")
        
        # Suggest fixes for missing keys
        if missing_keys:
            suggestions.append("Missing configuration keys:")
            for section, key in missing_keys:
                if section in self.SECTION_TEMPLATES and key in self.SECTION_TEMPLATES[section]:
                    value = self.SECTION_TEMPLATES[section][key]
                    suggestions.append(f"  [{section}] {key} = {value}")
                else:
                    suggestions.append(f"  [{section}] {key} = your_value_here")
            suggestions.append("")
        
        # Suggest fixes for invalid values
        if invalid_values:
            suggestions.append("Invalid configuration values:")
            for error in invalid_values:
                if error.suggestion:
                    suggestions.append(f"  {error.suggestion}")
            suggestions.append("")
        
        # Check for potential typos in existing config
        self._analyze_potential_typos(config, suggestions)
        
        return suggestions
    
    def _get_valid_keys_for_section(self, section: str) -> List[str]:
        """Get list of valid configuration keys for a section."""
        if section in self.SECTION_TEMPLATES:
            return list(self.SECTION_TEMPLATES[section].keys())
        
        # Return common keys if section not in templates
        return ['api_key', 'model', 'host', 'port', 'timeout', 'service']
    
    def _suggest_openai_model(self, invalid_model: str) -> Optional[str]:
        """Suggest correct OpenAI model name."""
        valid_models = ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo']
        
        # Direct fuzzy matching
        matches = difflib.get_close_matches(invalid_model.lower(), 
                                          [m.lower() for m in valid_models], 
                                          n=1, cutoff=0.6)
        if matches:
            for model in valid_models:
                if model.lower() == matches[0]:
                    return model
        
        # Pattern matching
        if 'gpt4' in invalid_model.lower() or 'gpt-4' in invalid_model.lower():
            return 'gpt-4'
        elif 'gpt3' in invalid_model.lower() or '3.5' in invalid_model:
            return 'gpt-3.5-turbo'
        
        return None
    
    def _suggest_anthropic_model(self, invalid_model: str) -> Optional[str]:
        """Suggest correct Anthropic model name."""
        valid_models = ['claude-3-sonnet-20240229', 'claude-3-haiku-20240307', 'claude-3-opus-20240229']
        
        if 'claude' in invalid_model.lower():
            if 'sonnet' in invalid_model.lower() or '3' in invalid_model:
                return 'claude-3-sonnet-20240229'
            elif 'haiku' in invalid_model.lower():
                return 'claude-3-haiku-20240307'
            elif 'opus' in invalid_model.lower():
                return 'claude-3-opus-20240229'
        
        return 'claude-3-sonnet-20240229'  # Default
    
    def _suggest_ollama_model(self, invalid_model: str) -> Optional[str]:
        """Suggest correct Ollama model name."""
        common_models = ['llama2:7b', 'llama2:13b', 'codellama:7b', 'mistral:7b']
        
        # Check if it's missing the tag
        if ':' not in invalid_model and invalid_model.lower() in ['llama2', 'llama', 'codellama', 'mistral']:
            return f"{invalid_model.lower()}:7b"
        
        # Fuzzy matching
        matches = difflib.get_close_matches(invalid_model.lower(),
                                          [m.lower() for m in common_models],
                                          n=1, cutoff=0.6)
        if matches:
            for model in common_models:
                if model.lower() == matches[0]:
                    return model
        
        return None
    
    def _suggest_ollama_host(self, invalid_host: str) -> Optional[str]:
        """Suggest correct Ollama host URL."""
        if not invalid_host.startswith(('http://', 'https://')):
            if 'localhost' in invalid_host.lower():
                return 'http://localhost:11434'
            elif '127.0.0.1' in invalid_host:
                return 'http://127.0.0.1'
            else:
                return f'http://{invalid_host}'
        
        return None
    
    def _suggest_service_name(self, invalid_service: str) -> Optional[str]:
        """Suggest correct service name."""
        valid_services = ['openai', 'anthropic', 'ollama']
        
        matches = difflib.get_close_matches(invalid_service.lower(),
                                          valid_services,
                                          n=1, cutoff=0.6)
        return matches[0] if matches else None
    
    def _analyze_potential_typos(self, config: Dict[str, Any], suggestions: List[str]) -> None:
        """Analyze configuration for potential typos and add suggestions."""
        typo_suggestions = []
        
        # Check section names - suggest lowercase canonical form
        for section_name in config.keys():
            canonical_section = section_name.lower()
            if canonical_section in self.SECTION_NAMES and section_name != canonical_section:
                typo_suggestions.append(f"  Section '[{section_name}]' should be '[{canonical_section}]' (lowercase preferred)")
            elif section_name.lower() not in [s.lower() for s in self.SECTION_NAMES.keys()]:
                suggested = self.suggest_section_name(section_name)
                if suggested and suggested != section_name.lower():
                    typo_suggestions.append(f"  Section '[{section_name}]' might be '[{suggested}]'")
        
        # Check key names within sections
        for section_name, section_config in config.items():
            if isinstance(section_config, dict):
                valid_keys = self._get_valid_keys_for_section(section_name.lower())
                for key in section_config.keys():
                    if key.lower() not in [k.lower() for k in valid_keys]:
                        suggested = self.suggest_config_key(section_name.lower(), key)
                        if suggested and suggested != key.lower():
                            typo_suggestions.append(f"  Key '[{section_name}] {key}' might be '{suggested}'")
        
        if typo_suggestions:
            suggestions.append("Potential typos detected:")
            suggestions.extend(typo_suggestions)
            suggestions.append("")