#!/usr/bin/env python3
"""
Environment variable helper utility for Sync2NAS configuration.

This utility helps users discover supported environment variables and test their configuration.
"""

import os
import sys
from typing import Dict, Any, List
from utils.config.config_normalizer import ConfigNormalizer
from utils.config.config_validator import ConfigValidator
from utils.sync2nas_config import load_configuration


def list_supported_env_vars() -> None:
    """List all supported environment variables and their mappings."""
    normalizer = ConfigNormalizer()
    env_vars = normalizer.get_supported_env_vars()
    
    print("🔧 Supported Environment Variables")
    print("=" * 50)
    print()
    
    # Group by service
    services = {}
    for env_var, (section, key) in env_vars.items():
        if section not in services:
            services[section] = []
        services[section].append((env_var, key))
    
    for service, vars_list in sorted(services.items()):
        print(f"📋 {service.upper()} Configuration:")
        for env_var, key in sorted(vars_list):
            current_value = os.getenv(env_var)
            status = f"✅ {current_value}" if current_value else "❌ Not set"
            print(f"  {env_var:<35} -> [{service}] {key:<15} {status}")
        print()


def check_current_env_vars() -> None:
    """Check which environment variables are currently set."""
    normalizer = ConfigNormalizer()
    env_vars = normalizer.get_supported_env_vars()
    
    set_vars = []
    unset_vars = []
    
    for env_var in env_vars.keys():
        value = os.getenv(env_var)
        if value:
            set_vars.append((env_var, value))
        else:
            unset_vars.append(env_var)
    
    print("🌍 Current Environment Variable Status")
    print("=" * 50)
    print()
    
    if set_vars:
        print("✅ Set Variables:")
        for env_var, value in set_vars:
            # Mask sensitive values
            if 'api_key' in env_var.lower():
                masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"  {env_var}: {masked_value}")
            else:
                print(f"  {env_var}: {value}")
        print()
    
    if unset_vars:
        print("❌ Unset Variables:")
        for env_var in unset_vars:
            print(f"  {env_var}")
        print()
    
    print(f"📊 Summary: {len(set_vars)} set, {len(unset_vars)} unset")


def test_configuration(config_file: str = None) -> None:
    """Test the current configuration including environment variables."""
    print("🧪 Testing Configuration")
    print("=" * 50)
    print()
    
    try:
        # Load configuration
        if config_file:
            config = load_configuration(config_file, normalize=True)
            print(f"📁 Loaded config from: {config_file}")
        else:
            # Try default locations
            default_paths = ['config/sync2nas.ini', 'sync2nas.ini']
            config = None
            for path in default_paths:
                try:
                    config = load_configuration(path, normalize=True)
                    print(f"📁 Loaded config from: {path}")
                    break
                except FileNotFoundError:
                    continue
            
            if config is None:
                print("⚠️  No config file found, using environment variables only")
                config = {}
        
        # Validate configuration
        validator = ConfigValidator()
        result = validator.validate_llm_config(config)
        
        print()
        if result.is_valid:
            print("✅ Configuration is valid!")
        else:
            print("❌ Configuration has errors:")
            for error in result.errors:
                print(f"  • {error.message}")
                if error.suggestion:
                    print(f"    💡 {error.suggestion}")
        
        if result.warnings:
            print("\n⚠️  Warnings:")
            for warning in result.warnings:
                print(f"  • {warning}")
        
        if result.suggestions:
            print("\n💡 Suggestions:")
            for suggestion in result.suggestions:
                print(f"  • {suggestion}")
    
    except Exception as e:
        print(f"❌ Error testing configuration: {e}")


def generate_env_template() -> None:
    """Generate a template .env file with all supported variables."""
    normalizer = ConfigNormalizer()
    env_vars = normalizer.get_supported_env_vars()
    
    print("📝 Environment Variable Template")
    print("=" * 50)
    print()
    print("# Copy this template to create a .env file")
    print("# Uncomment and set the variables you need")
    print()
    
    # Group by service
    services = {}
    for env_var, (section, key) in env_vars.items():
        if section not in services:
            services[section] = []
        services[section].append((env_var, key))
    
    for service, vars_list in sorted(services.items()):
        print(f"# {service.upper()} Configuration")
        for env_var, key in sorted(vars_list):
            example_value = _get_example_value(service, key)
            print(f"# {env_var}={example_value}")
        print()


def _get_example_value(service: str, key: str) -> str:
    """Get example value for environment variable."""
    examples = {
        ('llm', 'service'): 'openai',
        ('openai', 'api_key'): 'sk-your-openai-api-key-here',
        ('openai', 'model'): 'gpt-4',
        ('openai', 'max_tokens'): '4000',
        ('openai', 'temperature'): '0.1',
        ('anthropic', 'api_key'): 'sk-ant-your-anthropic-api-key-here',
        ('anthropic', 'model'): 'claude-3-sonnet-20240229',
        ('anthropic', 'max_tokens'): '4000',
        ('anthropic', 'temperature'): '0.1',
        ('ollama', 'host'): 'http://localhost:11434',
        ('ollama', 'model'): 'llama2:7b',
        ('ollama', 'num_ctx'): '4096',
    }
    return examples.get((service, key), 'your-value-here')


def main():
    """Main CLI interface for the environment variable helper."""
    if len(sys.argv) < 2:
        print("🔧 Sync2NAS Environment Variable Helper")
        print("=" * 50)
        print()
        print("Usage:")
        print("  python -m utils.config.env_helper <command>")
        print()
        print("Commands:")
        print("  list      - List all supported environment variables")
        print("  check     - Check current environment variable status")
        print("  test      - Test current configuration")
        print("  template  - Generate .env file template")
        print()
        print("Examples:")
        print("  python -m utils.config.env_helper list")
        print("  python -m utils.config.env_helper check")
        print("  python -m utils.config.env_helper test")
        print("  python -m utils.config.env_helper test config/my-config.ini")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_supported_env_vars()
    elif command == 'check':
        check_current_env_vars()
    elif command == 'test':
        config_file = sys.argv[2] if len(sys.argv) > 2 else None
        test_configuration(config_file)
    elif command == 'template':
        generate_env_template()
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'list', 'check', 'test', or 'template'")


if __name__ == '__main__':
    main()