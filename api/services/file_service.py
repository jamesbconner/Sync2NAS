import logging
import os
from typing import List, Dict, Any
from services.db_implementations.db_interface import DatabaseInterface
from services.tmdb_service import TMDBService
from utils.file_routing import file_routing
from utils.filename_parser import parse_filename
from utils.file_filters import EXCLUDED_FILENAMES
from utils.show_adder import add_show_interactively
from services.llm_implementations.ollama_implementation import OllamaLLMService
from services.llm_implementations.openai_implementation import OpenAILLMService
from services.llm_implementations.llm_interface import LLMInterface as LLMService

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self, db: DatabaseInterface, tmdb: TMDBService, 
                 anime_tv_path: str, incoming_path: str):
        self.db = db
        self.tmdb = tmdb
        self.anime_tv_path = anime_tv_path
        self.incoming_path = incoming_path

    async def route_files(self, dry_run: bool = False, 
                         auto_add: bool = False, request=None) -> Dict[str, Any]:
        """Route files from incoming directory to show directories"""
        try:
            if auto_add:
                await self._auto_add_missing_shows(dry_run)

            llm_service = None
            llm_confidence_threshold = 0.7
            services = None
            config = None
            if request is not None and hasattr(request, "app") and hasattr(request.app, "state") and hasattr(request.app.state, "services"):
                services = request.app.state.services
            if services:
                llm_service = services.get("llm_service")
                config = services.get("config")
                if config and llm_service:
                    if isinstance(llm_service, OllamaLLMService):
                        section = "ollama"
                    elif isinstance(llm_service, OpenAILLMService):
                        section = "openai"
                    else:
                        section = None
                    if section and config.has_option(section, "llm_confidence_threshold"):
                        llm_confidence_threshold = config.getfloat(section, "llm_confidence_threshold")

            routed = file_routing(
                self.incoming_path, 
                self.anime_tv_path, 
                self.db, 
                self.tmdb, 
                dry_run=dry_run,
                llm_service=llm_service,
                llm_confidence_threshold=llm_confidence_threshold
            )

            return {
                "success": True,
                "files_routed": len(routed) if routed else 0,
                "files": [
                    {
                        "remote_path": item["original_path"],
                        "routed_path": item["routed_path"],
                        "show_name": item["show_name"],
                        "season": int(item["season"]) if item["season"] is not None else None,
                        "episode": int(item["episode"]) if item["episode"] is not None else None
                    }
                    for item in (routed or [])
                ],
                "message": f"{len(routed) if routed else 0} file(s) routed successfully"
            }
        except Exception as e:
            logger.error(f"Failed to route files: {e}")
            raise

    async def list_incoming_files(self) -> Dict[str, Any]:
        """List files in the incoming directory"""
        try:
            files = []
            if os.path.exists(self.incoming_path):
                for root, dirs, filenames in os.walk(self.incoming_path):
                    for filename in filenames:
                        if filename not in EXCLUDED_FILENAMES:
                            full_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(full_path, self.incoming_path)
                            files.append({
                                "name": filename,
                                "path": rel_path,
                                "full_path": full_path
                            })

            return {
                "success": True,
                "files": files,
                "count": len(files),
                "incoming_path": self.incoming_path
            }
        except Exception as e:
            logger.error(f"Failed to list incoming files: {e}")
            raise

    async def _auto_add_missing_shows(self, dry_run: bool) -> None:
        """
        Scan incoming files and auto-add missing shows to the database.

        Args:
            dry_run (bool): If True, simulate add-show operations without writing to the database or filesystem.

        Returns:
            None
        """
        try:
            seen = set()

            for root, _, filenames in os.walk(self.incoming_path):
                for fname in filenames:
                    if fname in EXCLUDED_FILENAMES:
                        continue

                    full_path = os.path.join(root, fname)
                    if not os.path.isfile(full_path):
                        continue

                    metadata = parse_filename(fname)
                    show_name = metadata["show_name"]

                    if not show_name or show_name in seen:
                        continue
                    seen.add(show_name)

                    if self.db.show_exists(show_name):
                        continue

                    logger.info(f"Auto-adding show: {show_name}")

                    try:
                        result = add_show_interactively(
                            show_name=show_name,
                            tmdb_id=None,
                            db=self.db,
                            tmdb=self.tmdb,
                            anime_tv_path=self.anime_tv_path,
                            dry_run=dry_run,
                            override_dir=False,
                        )
                        
                        if not dry_run:
                            logger.info(f"Auto-added: {show_name}")
                        else:
                            logger.info(f"[DRY RUN] Would auto-add: {show_name}")
                            
                    except Exception as e:
                        logger.error(f"Failed to auto-add show '{show_name}': {e}")

        except Exception as e:
            logger.error(f"Failed to auto-add missing shows: {e}")
            raise 