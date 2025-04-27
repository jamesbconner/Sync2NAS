# Database Service Testing Philosophy

## Purpose
The goal of the database service tests is to ensure **correct behavior** across all layers of the database abstraction, regardless of the underlying database technology.

Tests are focused on **our own service contracts** — not on the correctness of the underlying SQLite, PostgreSQL, or Milvus libraries, which are already externally tested.

We validate that:
- SQL operations produce the expected results
- Transactions are atomic and safe
- Edge cases (e.g., missing records, failed inserts) are handled gracefully
- The interface contract (`DatabaseInterface`) is honored

## Architecture Context

Our database layer follows a **factory-based**, **interface-driven** design:
- `DatabaseInterface` defines the universal database operations (abstract methods)
- `SQLiteDBService`, `PostgresDBService`, and `MilvusDBService` implement the interface
- `create_db_service()` (factory) chooses the correct implementation at runtime

This enables:
- Swappable database engines without modifying the application code
- Easier extension if new database types are added
- Consistent testing regardless of backend

Therefore, we test **against the service methods**, not the database directly.

## Testing Style and Structure

### Principles
- **Behavior over implementation:** Tests validate *what* happens, not *how* it's done internally.
- **Isolation:** Tests use temporary databases (e.g., `tmp_path`) to ensure clean, independent runs.
- **Factory loading:** Where possible, instantiate services through the factory (`create_db_service()`) to simulate real-world configuration.
- **Explicit edge case handling:** Missing records, empty queries, duplicate inserts, and error conditions are tested deliberately.
- **No direct SQL manipulation:** All interactions are done through the service methods, not raw SQL.

### Common Patterns
- Fixtures provide:
  - Temporary SQLite database files
  - Preloaded sample data for shows, episodes, files
- Assertions check:
  - Correct record insertion
  - Correct retrieval
  - Correct behavior when querying missing or invalid data
  - No unexpected side effects (e.g., dirty writes, leaks)

### Mocking
- **Minimal mocking:** We rarely mock SQLite itself.
- Instead, we allow real transactions on temporary databases.
- We *may* mock adapters (`sqlite3.register_adapter`) for special error tests.

## Out of Scope
- We do **not** test SQLite, Postgres, or Milvus libraries themselves.
- We assume the database backends are correctly installed and operational.
- Connection pooling, clustering, or replication behaviors are not tested here.

## Related Files
- `services/db_service.py`
- `services/db_factory.py`
- `services/db_implementations/sqlite_implementation.py`
- `tests/services/test_db_service.py`
- `tests/services/test_db_service_sftp.py` (SFTP-related db interactions)

## Philosophy Summary

✅ **Database Service Testing ensures our abstraction remains stable and reliable across any supported backend, validating business rules, not SQL engines.**

# 🔗 Related Links
- [Main README](../README.md)