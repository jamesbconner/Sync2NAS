# TMDB Service Testing Philosophy

## Purpose
The goal of the TMDB service tests is to ensure **correct behavior** of our TMDBService wrapper over the third-party TMDB API (`tmdbsimple`).

Tests validate that:
- API calls are constructed correctly
- Error handling is robust (network errors, HTTP errors, unexpected responses)
- The expected data structures are returned consistently
- Internal helper logic (fallbacks, grouping) behaves as intended

We are **not** testing TMDB itself.  
We focus only on **our own interface and behaviors**.

## Architecture Context

Our TMDB layer is structured as a simple **service class**:
- `TMDBService` wraps the `tmdbsimple` library
- Exposes methods for:
  - Searching for shows
  - Fetching show metadata
  - Fetching season, episode, and episode group metadata
- Converts raw TMDB responses into structured dictionaries used internally

This structure:
- Shields the rest of the application from direct dependency on `tmdbsimple`
- Provides a controlled layer for retry, error handling, and future enhancements

Thus, **the service’s contract** — not TMDB’s — is what our tests protect.

## Testing Style and Structure

### Principles
- **Behavior over API internals:** Tests validate *what* our service returns or raises, not *how* `tmdbsimple` or TMDB API work.
- **Controlled mocking:** All external API calls (`.info()`, `.tv()`, etc.) are fully mocked.
- **Error resiliency:** We simulate HTTP errors, general exceptions, and missing fields to ensure defensive programming.
- **Structured result checking:** We assert that outputs have the correct keys, types, and contents, matching expected schema.

### Common Patterns
- Fixtures provide:
  - Pre-initialized `TMDBService` instances
- Mocking:
  - `patch` is used to replace `tmdbsimple` methods like `Search.tv()`, `TV.info()`, etc.
- Assertions check:
  - Correct parsing of normal TMDB responses
  - Proper fallback behavior when API fields are missing
  - Expected `None` returns or graceful degradation on failure

### Edge Case Testing
- Empty results
- Missing fields
- Non-standard API responses
- Simulated network and server errors

This ensures the service remains robust even if TMDB’s API evolves unexpectedly.

## Out of Scope
- We do **not** validate TMDB API schemas
- We do **not** test TMDB availability or rate limits
- We do **not** perform live integration tests hitting the real TMDB endpoints

(If live testing is needed, it should be done via separate integration test suites.)

## Related Files
- `services/tmdb_service.py`
- `tests/services/test_tmdb_service.py`

## Philosophy Summary

✅ **TMDB Service Testing ensures our API wrapper remains resilient and reliable, abstracting away third-party instability while providing consistent internal contracts.**

# 🔗 Related Links
- [Main README](../README.md)