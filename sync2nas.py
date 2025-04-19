from cli.main import sync2nas_cli

# ────────────────────────────────────────────────
# ToDo List
# ────────────────────────────────────────────────
# ToDo: Check downloaded file against AniDB hash to confirm file integrity and correctly identify episode
# ToDo: Check inventory hashes against AniDB hashes to confirm file integrity and correctly identify episode
# ToDo: Inventory check against episodes table to identify missing episodes
# ToDo: Filename transformer to convert absolute episode number to relative season/episode number (Jellyfin)
# ToDo: Check for new seasons of shows existing in the inventory on AniDb (periodic pull of AniDB)
# ToDo: Fix the downloader to use the file filtering function
# ToDo: Add a de-deupe function to identify duplicate show/episodes in the inventory for pruning
# ToDo: Rework special character handling in show names (primary and aliases)
# ToDo: Add a function to check for and handle show/episode renames and updates to the database
# ToDo: Add IMDB, TVDB and AniDB APIs as optional sources for show information if TMDB info missing
# ToDo: Better checks for handling specials and OVA's 
# ToDo: Add genre, language and other identifiers to the search and fix-show functions
# ToDo: MCP LLM integration for show and episode filename parsing ... why regex it when you can ask the LLM?
# ToDo: MCP Server integration with TMDB, AniDB, TVDB, IMDB, etc. to get show and episode information
# ToDo: MCP Server integration with database backend to update/add shows, episodes, etc. Already supports SQLite
# ToDo: Try vector DB for similarity search and recommendations ... Milvus, Chroma, Qdrant, Weaviate, Faiss, etc.
# ToDo: Semantic search and content-based retrieval of shows and episodes
# ToDo: MCP Server RSS Feed integration for new show notifications


if __name__ == '__main__':
    sync2nas_cli()