# Sync2NAS Architecture

This document provides an overview of the Sync2NAS system architecture, components, and design patterns.

## System Overview

Sync2NAS is built using a modular, service-oriented architecture that separates concerns and enables easy testing and extension.

## Layers and Components

### 1. CLI Layer (`cli/`)

- **Purpose:** User-facing command-line interface for all operations.
- **Pattern:** Each command is a separate module, dynamically discovered and registered.
- **Context:** Uses a context object to inject configuration and services into commands.

**Example:**  
`python sync2nas.py add-show "Breaking Bad" --tmdb-id 1396`

---

### 2. API Layer (`api/`)

- **Purpose:** REST API (FastAPI) for programmatic access and integration.
- **Structure:**  
  - `main.py`: FastAPI app and router registration.
  - `routes/`: Endpoint modules (shows, files, admin, etc.).
  - `models/`: Pydantic request/response schemas.
  - `services/`: API-specific business logic.

**API Docs:**  
- Interactive: `/docs`  
- ReDoc: `/redoc`  
- See [api/README.md](../api/README.md) for details.

---

### 3. Service Layer (`services/`)

- **Purpose:** Core business logic and integrations.
- **Components:**
  - `db_factory.py`: Database backend selection.
  - `tmdb_service.py`: TMDB API integration.
  - `sftp_service.py`: SFTP file transfer.
  - `llm_factory.py`: LLM backend selection.
  - `db_implementations/`: Backend implementations (SQLite, PostgreSQL, Milvus).

**Pattern:**  
- Factory for backend selection.
- Strategy for parsing (regex vs LLM).
- Adapter for external APIs.

---

### 4. Model Layer (`models/`)

- **Purpose:** Data models for shows, episodes, and API schemas.
- **Pattern:**  
  - Data classes for shows and episodes.
  - Pydantic models for API validation.

---

### 5. Utility Layer (`utils/`)

- **Purpose:** Helper functions for configuration, logging, file parsing, etc.
- **Examples:**  
  - `sync2nas_config.py`: Loads and validates config.
  - `logging_config.py`: Sets up logging.
  - `file_routing.py`: Handles file routing logic.
  - `episode_updater.py`, `show_adder.py`: Business logic helpers.

---

### 6. Database Layer (`services/db_implementations/`)

- **Purpose:** Pluggable database backends.
- **Supported:**  
  - SQLite (default, file-based)
  - PostgreSQL (for large/multi-user setups)
  - Milvus (vector search, experimental)
- **Pattern:**  
  - All backends implement a common interface (`db_interface.py`).

---

## Data Flow Examples

### File Routing

1. **User Command:** `route-files`
2. **File Discovery:** Scan incoming directory.
3. **Filename Parsing:** Use regex or LLM to extract show/episode.
4. **Show/Episode Lookup:** Query database for show/episode.
5. **File Move:** Move file to correct destination.
6. **Database Update:** Update file tracking tables.

---

### Show Addition

1. **User Command:** `add-show`
2. **TMDB Search:** Find show by name or TMDB ID.
3. **Directory Creation:** Create show directory.
4. **Database Update:** Add show and episodes to database.

---

### API Request

1. **HTTP Request:** e.g., `POST /api/shows/`
2. **Route Handler:** Validates and parses request.
3. **Service Layer:** Executes business logic.
4. **Database Layer:** Reads/writes data.
5. **Response:** Returns JSON result.

---

## Design Patterns

- **Factory:** Database backend selection.
- **Strategy:** Regex vs LLM filename parsing.
- **Dependency Injection:** Context objects for CLI/API.
- **Command:** CLI command modules.
- **Service:** Encapsulated business logic.

---

## Error Handling

- **Graceful Fallback:** LLM parsing falls back to regex.
- **Comprehensive Logging:** All layers log actions and errors.
- **User-Friendly Messages:** CLI/API return clear errors.

---

## Extensibility

- **Add CLI/API commands:** Create new modules in `cli/` or `api/routes/`.
- **Add database backends:** Implement `DatabaseInterface` and register in `db_factory.py`.
- **Add integrations:** Create new service modules.

---

## Testing

- **Service contract tests** for all backends.
- **Mocking** for external APIs (TMDB, SFTP, LLM).
- **CLI and API endpoint tests** in `tests/`.

---

## Security

- **SSH key authentication** for SFTP.
- **API key management** for TMDB/OpenAI.
- **Input validation** and error handling throughout.

---

## References

- [API Documentation](../api/README.md)
- [Database Backends Guide](database_backends.md)
- [File Routing Guide](file_routing.md)
- [SFTP Service Philosophy](SFTP_Test_Philosophy.md)
- [TMDB Service Philosophy](TMDB_Test_Philosophy.md)
- [Database Service Philosophy](Database_Test_Philosophy.md)
- [Services Test Coverage Matrix](Services_Test_Coverage_Matrix.md)

---

*For more details on any component, see the corresponding module or documentation file.*

# LLM Architecture

**Note:** The old `services/llm_service.py` is deprecated and should not be used. All LLM logic is now handled via the factory/interface/implementation pattern described below.

## Overview
The LLM filename parsing system is now modular and backend-agnostic, supporting both local (Ollama) and remote (OpenAI) LLMs. The backend is selected via configuration, and all implementations share common logic via a base class.

## Components

### Factory (`services/llm_factory.py`)
- Exposes `create_llm_service(config)`.
- Reads the `[llm]` section of the config to select the backend (`ollama` or `openai`).
- Instantiates and returns the correct implementation.

### Base Class (`services/llm_implementations/base_llm_service.py`)
- Inherits from `LLMInterface`.
- Implements shared logic for:
  - Prompt creation
  - Result validation and cleaning
  - Fallback parsing
  - Batch parsing
- All LLM implementations inherit from this class.

### Implementations
- `OllamaLLMService`: Uses the local Ollama server and model. Reads model and confidence threshold from config.
- `OpenAILLMService`: Uses the OpenAI API. Reads model, API key, and other options from config.
- Both only override backend-specific logic and the system prompt.

### Adding a New LLM Backend
1. Implement a new class inheriting from `BaseLLMService`.
2. Add backend-specific logic and system prompt.
3. Update the factory to recognize the new backend in config and instantiate your class.

## Configuration-Driven
- The backend, model, and options are all set in the config file. No code changes are needed to switch backends.

## API and CLI Integration
- Both API and CLI use the factory to instantiate the LLM service based on the loaded config.
- The LLM service is passed via context or dependency injection, ensuring a single instance is used per run.

## Migration Note
If you are upgrading from a previous version:
- The old `services/llm_service.py` is deprecated and should be removed.
- All LLM logic is now handled via the factory/interface/implementation pattern described above.
- Update your config to use the new `[llm]`, `[ollama]`, and `[openai]` sections.