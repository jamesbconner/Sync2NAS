import logging
from typing import List, Dict, Any
from services.sftp_service import SFTPService
from services.db_implementations.db_interface import DatabaseInterface
from utils.sync2nas_config import parse_sftp_paths
from utils.sftp_orchestrator import download_from_remote as downloader

logger = logging.getLogger(__name__)


class RemoteService:
    def __init__(self, sftp: SFTPService, db: DatabaseInterface, config: Dict[str, Any]):
        self.sftp = sftp
        self.db = db
        self.config = config

    async def download_from_remote(self, dry_run: bool = False) -> Dict[str, Any]:
        """Download files from remote SFTP server"""
        try:
            remote_paths = parse_sftp_paths(self.config)
            if not remote_paths:
                raise ValueError("No SFTP paths defined in config [SFTP] section")

            incoming_path = self.config["Transfers"]["incoming"]

            with self.sftp as s:
                downloader(
                    sftp=s,
                    db=self.db,
                    remote_paths=remote_paths,
                    incoming_path=incoming_path,
                    dry_run=dry_run
                )

            return {
                "success": True,
                "files_downloaded": 0,  # TODO: Get actual count from downloader
                "message": "Download completed successfully" if not dry_run else "Dry run completed"
            }
        except Exception as e:
            logger.error(f"Failed to download from remote: {e}")
            raise

    async def list_remote_files(self, path: str = None, recursive: bool = False,
                              populate_sftp_temp: bool = False, 
                              dry_run: bool = False) -> Dict[str, Any]:
        """List files on remote SFTP server"""
        try:
            remote_path = path if path else self.config["SFTP"]["path"]

            with self.sftp as sftp:
                if recursive:
                    files = sftp.list_remote_files_recursive(remote_path)
                else:
                    files = sftp.list_remote_dir(remote_path)

                if populate_sftp_temp and not dry_run:
                    # Convert timestamps to strings for database storage
                    files_for_db = []
                    for f in files:
                        file_copy = f.copy()
                        # Handle modified_time
                        if hasattr(file_copy['modified_time'], 'isoformat'):
                            file_copy['modified_time'] = file_copy['modified_time'].isoformat()
                        # Handle fetched_at
                        if hasattr(file_copy['fetched_at'], 'isoformat'):
                            file_copy['fetched_at'] = file_copy['fetched_at'].isoformat()
                        files_for_db.append(file_copy)
                    
                    self.db.insert_sftp_temp_files(files_for_db)

                return {
                    "success": True,
                    "files": [
                        {
                            "name": f["name"],
                            "size": f.get("size"),
                            "modified_time": f.get("modified_time"),
                            "fetched_at": f.get("fetched_at")
                        }
                        for f in files
                    ],
                    "count": len(files),
                    "path": remote_path
                }
        except Exception as e:
            logger.error(f"Failed to list remote files: {e}")
            raise

    async def get_connection_status(self) -> Dict[str, Any]:
        """Check SFTP connection status"""
        try:
            with self.sftp as sftp:
                # Try a simple operation to test connection
                sftp.list_remote_dir("/")
                return {
                    "success": True,
                    "status": "connected",
                    "host": self.config["SFTP"]["host"],
                    "port": self.config["SFTP"]["port"]
                }
        except Exception as e:
            return {
                "success": False,
                "status": "disconnected",
                "error": str(e),
                "host": self.config["SFTP"]["host"],
                "port": self.config["SFTP"]["port"]
            } 