from cli.main import sync2nas_cli

# ────────────────────────────────────────────────
# TODO List
# ────────────────────────────────────────────────
# Done: Database backup function
# Done: Add list and search functions from the database
# Done: Add search function from the TMDB API
# TODO: Add a function to check for and handle show/episode renames and updates to the database
# TODO: Check downloaded file against AniDB hash to confirm file integrity and correctly identify episode
# TODO: Check inventory hashes against AniDB hashes to confirm file integrity and correctly identify episode
# TODO: Inventory check against episodes table to identify missing episodes
# TODO: Filename transformer to convert absolute episode number to relative season/episode number (Jellyfin)
# TODO: Check for new seasons of shows existing in the inventory on AniDb (periodic pull of AniDB)
# TODO: Add a de-deupe function to identify duplicate show/episodes in the inventory for pruning
# TODO: Rework special character handling in show names (primary and aliases)
# TODO: Add a function to check for and handle show/episode renames and updates to the database
# TODO: Add IMDB, TVDB and AniDB APIs as optional sources for show information if TMDB info missing
# TODO: Better checks for handling specials and OVA's 
# TODO: Add genre, language and other identifiers to the search and fix-show functions
# TODO: MCP LLM integration for show and episode filename parsing ... why regex it when you can ask the LLM?
# TODO: MCP Server integration with TMDB, AniDB, TVDB, IMDB, etc. to get show and episode information
# TODO: MCP Server integration with database backend to update/add shows, episodes, etc. Already supports SQLite
# TODO: Try vector DB for similarity search and recommendations ... Milvus, Chroma, Qdrant, Weaviate, Faiss, etc.
# TODO: Semantic search and content-based retrieval of shows and episodes
# TODO: MCP Server RSS Feed integration for new show notifications
# TODO: Add discord integration for notifications of scene releases
# TODO: Implement Anthropic LLM support in the LLM factory and as a service implementation


if __name__ == '__main__':
    sync2nas_cli()