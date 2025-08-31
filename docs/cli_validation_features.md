# CLI Configuration Validation Features

## Overview

The Sync2NAS CLI now includes comprehensive configuration validation and health checking to ensure all services are properly configured before use.

## New CLI Options

### --skip-validation
Skip configuration validation and health checks for troubleshooting purposes.

```bash
sync2nas --skip-validation [command]
```

Use this flag when:
- Troubleshooting configuration issues
- Services are temporarily unavailable
- You need to run commands that don't require all services

## Startup Validation

The CLI now performs the following validation steps during startup:

1. **Configuration Loading**: Loads and normalizes configuration with environment variable overrides
2. **LLM Service Validation**: Validates LLM configuration and tests connectivity
3. **Service Initialization**: Initializes database, SFTP, and TMDB services with error handling
4. **Health Checks**: Performs connectivity tests for critical services

## Error Handling

### Configuration Errors
When configuration validation fails, the CLI will:
- Display detailed error messages with specific issues
- Provide actionable suggestions for fixing problems
- Exit with appropriate error codes for automation

### Service Failures
When services fail to initialize:
- Non-critical services log warnings but allow startup to continue
- Critical services (like LLM) will prevent startup unless `--skip-validation` is used
- Clear error messages indicate which services are unavailable

## Context Validation Helpers

New helper functions are available for CLI commands:

### validate_context_for_command()
Validates that required services are available in the context.

### get_service_from_context()
Safely retrieves services from context with proper error handling.

## Config Check Command

Use the `config-check` command to validate your configuration:

```bash
# Check all configured services
sync2nas config-check

# Check specific service
sync2nas config-check -s openai

# Skip connectivity tests
sync2nas config-check --skip-connectivity
```

## Troubleshooting

If you encounter startup issues:

1. Run `sync2nas config-check` to diagnose configuration problems
2. Use `--skip-validation` flag to bypass validation temporarily
3. Check logs with `-v` or `-vv` for detailed diagnostic information
4. Verify environment variables are set correctly for sensitive configuration