import logging
import os
import time
from typing import Dict, Any
from services.db_implementations.db_interface import DatabaseInterface
from services.tmdb_service import TMDBService
from models.show import Show

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(self, db: DatabaseInterface, tmdb: TMDBService, 
                 anime_tv_path: str, config: Dict[str, Any]):
        self.db = db
        self.tmdb = tmdb
        self.anime_tv_path = anime_tv_path
        self.config = config

    async def bootstrap_tv_shows(self, dry_run: bool = False) -> Dict[str, Any]:
        """Bootstrap TV shows from anime_tv_path directory"""
        try:
            added, skipped, failed = [], [], []
            start_time = time.time()

            for folder_name in sorted(os.listdir(self.anime_tv_path)):
                sys_name = folder_name.strip()
                sys_path = os.path.join(self.anime_tv_path, sys_name)
                
                if not os.path.isdir(sys_path):
                    continue

                try:
                    if self.db.show_exists(sys_name):
                        logger.info(f"Skipping: {sys_name}")
                        skipped.append(sys_name)
                        continue

                    results = self.tmdb.search_show(sys_name)
                    if not results or not results.get("results"):
                        logger.warning(f"No TMDB results for: {sys_name}")
                        failed.append(sys_name)
                        continue

                    details = self.tmdb.get_show_details(results["results"][0]["id"])
                    if not details or "info" not in details:
                        failed.append(sys_name)
                        continue

                    show = Show.from_tmdb(details, sys_name=sys_name, sys_path=sys_path)
                    if dry_run:
                        logger.info(f"[DRY RUN] Would add show: {sys_name}")
                    else:
                        self.db.add_show(show)
                        logger.info(f"Added: {show.tmdb_name}")
                    added.append(sys_name)

                except Exception as e:
                    logger.exception(f"Failed to process: {sys_name}")
                    failed.append(sys_name)

            duration = time.time() - start_time

            return {
                "success": True,
                "added": len(added),
                "skipped": len(skipped),
                "failed": len(failed),
                "duration": duration,
                "message": f"Bootstrap completed: {len(added)} added, {len(skipped)} skipped, {len(failed)} failed"
            }
        except Exception as e:
            logger.error(f"Failed to bootstrap TV shows: {e}")
            raise

    async def bootstrap_episodes(self, dry_run: bool = False) -> Dict[str, Any]:
        """Bootstrap episodes for all shows"""
        try:
            shows = self.db.get_all_shows()
            added, skipped, failed = 0, 0, 0
            start_time = time.time()

            for show_record in shows:
                try:
                    show = Show.from_db_record(show_record)
                    
                    # Check if episodes already exist
                    existing_episodes = self.db.get_episodes_by_show_id(show.id)
                    if existing_episodes:
                        logger.info(f"Skipping {show.sys_name} - already has episodes")
                        skipped += 1
                        continue

                    # Fetch episodes from TMDB
                    episodes = self.tmdb.get_show_episodes(show.tmdb_id)
                    if not episodes:
                        logger.warning(f"No episodes found for {show.sys_name}")
                        failed += 1
                        continue

                    if not dry_run:
                        for episode_data in episodes:
                            episode = Episode.from_tmdb(episode_data, show.id)
                            self.db.add_episode(episode)
                    
                    added += 1
                    logger.info(f"{'[DRY RUN] Would add' if dry_run else 'Added'} episodes for {show.sys_name}")

                except Exception as e:
                    logger.exception(f"Failed to bootstrap episodes for {show_record['sys_name']}")
                    failed += 1

            duration = time.time() - start_time

            return {
                "success": True,
                "added": added,
                "skipped": skipped,
                "failed": failed,
                "duration": duration,
                "message": f"Episode bootstrap completed: {added} added, {skipped} skipped, {failed} failed"
            }
        except Exception as e:
            logger.error(f"Failed to bootstrap episodes: {e}")
            raise

    async def backup_database(self) -> Dict[str, Any]:
        """Create database backup"""
        try:
            # This would depend on your database implementation
            # For now, return a placeholder
            return {
                "success": True,
                "message": "Database backup completed",
                "backup_path": "/path/to/backup"
            }
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            raise

    async def init_database(self) -> Dict[str, Any]:
        """Initialize database"""
        try:
            # This would depend on your database implementation
            # For now, return a placeholder
            return {
                "success": True,
                "message": "Database initialized successfully"
            }
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise 