# 📋 Service Tests Coverage Matrix

This document summarizes unit test coverage for the major **service layer components** of the Sync2NAS project.  
It provides a checklist of critical behaviors each service implements and the corresponding test coverage.

---

## ✅ SFTPService Tests

| Feature / Functionality                         | Test Name(s)                                 | Notes                                               |
|:-------------------------------------------------|:---------------------------------------------|:----------------------------------------------------|
| List remote dir (filter media files & folders)   | `test_list_remote_dir_filters_properly`      | Filters out recent files, excluded types and names  |
| List remote files non-recursively                | `test_list_remote_files_filters_properly`    | Similar logic as `list_remote_dir`                  |
| List remote files recursively                    | `test_list_remote_files_recursive_correctly`| Recurses properly into subdirectories              |
| Download single file                             | `test_download_file`                         | Verifies correct SFTP `get` call                    |
| Download entire directory                        | `test_download_dir`                          | Verifies recursive download with mocked structure   |

---

## ✅ DBService Tests

| Feature / Functionality                         | Test Name(s)                                         | Notes                                             |
|:-------------------------------------------------|:-----------------------------------------------------|:--------------------------------------------------|
| Add show and check existence                    | `test_add_show_and_query`, `test_show_exists_alias_match` | Includes alias matching                        |
| Add episode and check existence                 | `test_add_episodes_and_query`, `test_get_episode_by_absolute_number` | Standard episode addition and lookup        |
| Delete show and associated episodes             | `test_delete_show_and_episodes`, `test_delete_nonexistent_show_and_episodes` | Safe even if nonexistent            |
| Add inventory files and retrieve                | `test_add_inventory_files`                          | Adds file metadata and verifies retrieval        |
| Add downloaded files and retrieve               | `test_add_downloaded_files`                         | Adds file metadata and verifies retrieval        |
| Get SFTP file diffs                             | `test_get_sftp_diffs_returns_expected_new_files`    | Diffing temp vs downloaded files                 |
| SQLite adapter error handling                   | `test_sqlite_adapter_registration_error`            | Simulates adapter failures gracefully             |
| Connection error handling                       | `test_connection_error_handling`                    | Simulates DB connection failure                   |
| Lookup show by system name or alias             | `test_get_show_by_sys_name`, `test_get_show_by_alias`| Alias and system name search                      |

---

## ✅ TMDBService Tests

| Feature / Functionality                         | Test Name(s)                                         | Notes                                             |
|:-------------------------------------------------|:-----------------------------------------------------|:--------------------------------------------------|
| Search show by name                             | `test_search_show`, `test_search_show_returns_empty_results` | Normal and empty search results tested      |
| Handle search errors (HTTP, general)            | `test_search_show_http_error`, `test_search_show_general_error` | Search resilience                             |
| Get show full details (info, episode groups)    | `test_get_show_details`, `test_get_show_details_missing_fields`, `test_get_show_details_http_error`, `test_get_show_details_general_error` | Complete coverage and error handling         |
| Get season details                              | `test_get_show_season_details`, `test_get_show_season_details_empty`, `test_get_show_season_details_http_error`, `test_get_show_season_details_general_error` | Season metadata retrieval                   |
| Get episode details                             | `test_get_show_episode_details`, `test_get_show_episode_details_returns_none`, `test_get_show_episode_details_http_error`, `test_get_show_episode_details_general_error` | Episode-specific retrieval                 |
| Get episode group details                       | `test_get_episode_group_details`, `test_get_episode_group_details_http_error`, `test_get_episode_group_details_general_error` | Testing for grouping metadata                |

---

# 📚 Service Summary

| Service        | Core Features Covered | Error/Edge Cases Covered | Notes                                           |
|:---------------|:----------------------|:-------------------------|:------------------------------------------------|
| **SFTPService** | ✅ (All major operations) | ❌ (decorator failure modes not deeply tested) | Focused on file ops; retry logic assumed |
| **DBService**  | ✅ (Show, episode, inventory, diffs) | ✅ (Adapter errors, connection fails)          | Very strong coverage overall                      |
| **TMDBService** | ✅ (Show search/detail/episode/group) | ✅ (HTTP and general errors)                    | Mocks external API properly and robustly          |

---

# 🔗 Related Links
- [Main README](../README.md)

## LLM Services
- Tests should cover:
  - LLM factory: correct backend selection based on config
  - Base class: prompt creation, validation, fallback, batch parsing
  - Ollama and OpenAI implementations: backend-specific logic, system prompt
  - CLI and API integration: ensure LLM is used when configured
  - Fallback to regex when LLM is not confident or fails
  - Error handling for misconfiguration or backend errors
  - Migration: tests should ensure legacy LLMService code is removed and new pattern is used
  - No code or tests should reference the deprecated services/llm_service.py or LLMService class