# File Routing Guide

This guide explains how Sync2NAS routes files from the incoming directory to organized show directories, including both traditional regex and AI-powered filename parsing.

---

## What is File Routing?

File routing is the process of moving downloaded files from your "incoming" directory to their correct destination folders in your media library, based on show name, season, and episode information extracted from the filename.

---

## How File Routing Works

1. **File Discovery:**  
   Sync2NAS scans the configured incoming directory (and subdirectories) for new files.

2. **Filename Parsing:**  
   For each file, Sync2NAS attempts to extract:
   - Show name
   - Season number (if present)
   - Episode number (if present)

   This is done using:
   - **Regex patterns** (default, fast, works for standard formats)
   - **LLM (OpenAI GPT) parsing** (optional, for complex or non-standard filenames)

3. **Show Matching:**  
   The extracted show name is matched against the database using:
   - Exact name matches
   - Alias matches
   - Partial name matches (if enabled)

4. **Episode Resolution:**  
   If season/episode information is missing or ambiguous, Sync2NAS:
   - Looks up episode information in the database
   - Refreshes episode data from TMDB if needed
   - Converts absolute episode numbers to season/episode format (for anime)

5. **File Movement:**  
   Files are moved to the appropriate show directory structure, e.g.:
   ```
   One Piece/
     Season 20/
       One.Piece.Episode.1000.mkv
   ```

6. **Database Update:**  
   The database is updated to reflect the new file locations and status.

---

## Filename Parsing Methods

### 1. Regex Parsing (Default)

Sync2NAS includes comprehensive regex patterns for common filename formats, such as:
- `Show.Name.S01E01.1080p.mkv`
- `Show Name - 01.mkv`
- `[Group] Show Name - 01 [1080p].mkv`

Regex parsing is fast and works well for standard scene and fansub formats.

### 2. LLM (AI) Parsing (Optional)

For complex or non-standard filenames, Sync2NAS can use OpenAI's GPT models for intelligent parsing.

**Benefits:**
- Handles messy, ambiguous, or highly variable filenames
- Provides a confidence score and reasoning for each parse
- Falls back to regex if the LLM is unsure

**Example:**
```
Filename: [Erai-raws] One Piece - 1000 [1080p][Multiple Subtitle][5312D81B].mkv
LLM Output: {"show_name": "One Piece", "season": null, "episode": 1000, "confidence": 0.95}
```

---

## Enabling LLM Parsing

1. Add your OpenAI API key to your config:
   ```ini
   [OpenAI]
   api_key = your_openai_api_key_here
   model = gpt-3.5-turbo
   max_tokens = 150
   temperature = 0.1
   ```

2. Use the `--use-llm` flag with the `route-files` command:
   ```bash
   python sync2nas.py route-files --use-llm
   ```

3. (Optional) Set a custom confidence threshold:
   ```bash
   python sync2nas.py route-files --use-llm --llm-confidence 0.8
   ```

---

## Usage Examples

### Standard Routing (Regex)
```bash
python sync2nas.py route-files
```

### AI-Powered Routing (LLM)
```bash
python sync2nas.py route-files --use-llm
```

### Auto-add Unknown Shows
```bash
python sync2nas.py route-files --auto-add
```

### Dry Run (Preview Actions)
```bash
python sync2nas.py route-files --dry-run
python sync2nas.py route-files --use-llm --dry-run
```

---

## Troubleshooting

- **File not routed:**  
  - Check that the show exists in the database (use `add-show` or `--auto-add`)
  - Try enabling LLM parsing for complex filenames

- **Wrong destination:**  
  - Check the filename format and parsing result (use `--dry-run` and verbose logging)

- **Low confidence (LLM):**  
  - Lower the confidence threshold with `--llm-confidence`
  - Review the LLM reasoning in the dry run output

- **Performance issues:**  
  - LLM parsing is slower and uses OpenAI API credits; use only when needed

---

## Best Practices

- Use consistent naming conventions for your files when possible.
- Add shows manually for best results, especially for ambiguous or multi-title series.
- Keep episode information up to date by running `bootstrap-episodes` or `update-episodes`.
- Use dry runs to preview routing actions before moving files.
- Monitor logs for parsing errors or unmatched files.

---

## Advanced

- You can extend or modify the regex patterns in `utils/file_routing.py` for custom formats.
- The LLM prompt can be customized in `services/llm_service.py` for special parsing needs.
- Future versions may support custom routing rules for different file types.

---

For more details, see the main [README.md](../README.md) and the [API documentation](../api/README.md).
