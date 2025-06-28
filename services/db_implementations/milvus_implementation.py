import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)
from services.db_implementations.db_interface import DatabaseInterface
from models.show import Show
from models.episode import Episode
from datetime import datetime

logger = logging.getLogger(__name__)

class MilvusDBService(DatabaseInterface):
    """Milvus implementation of the DatabaseInterface."""
    
    def __init__(self, host: str, port: str) -> None:
        """Initialize the Milvus connection.
        
        Args:
            host: Milvus server host
            port: Milvus server port
        """
        self.host = host
        self.port = port
        self.connection_alias = "default"
        connections.connect(
            alias=self.connection_alias,
            host=self.host,
            port=self.port
        )
        logger.info(f"Connected to Milvus server at {host}:{port}")

    def _create_collection_if_not_exists(self, collection_name: str, schema: CollectionSchema) -> Collection:
        """Create a collection if it doesn't exist."""
        if utility.has_collection(collection_name):
            return Collection(collection_name)
        
        collection = Collection(
            name=collection_name,
            schema=schema,
            using=self.connection_alias
        )
        logger.info(f"Created collection: {collection_name}")
        return collection

    def initialize(self) -> None:
        """Initialize the database schema."""
        # TV Shows collection
        tv_shows_schema = CollectionSchema([
            FieldSchema("id", DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema("sys_name", DataType.VARCHAR, max_length=255),
            FieldSchema("sys_path", DataType.VARCHAR, max_length=1024),
            FieldSchema("tmdb_name", DataType.VARCHAR, max_length=255),
            FieldSchema("tmdb_aliases", DataType.VARCHAR, max_length=1024),
            FieldSchema("tmdb_id", DataType.INT64),
            FieldSchema("tmdb_overview", DataType.VARCHAR, max_length=2048),
            FieldSchema("tmdb_status", DataType.VARCHAR, max_length=50),
            FieldSchema("tmdb_external_ids", DataType.VARCHAR, max_length=1024),
            # Store timestamps as strings in ISO format
            FieldSchema("tmdb_first_aired", DataType.VARCHAR, max_length=30),
            FieldSchema("tmdb_last_aired", DataType.VARCHAR, max_length=30),
            FieldSchema("tmdb_episodes_fetched_at", DataType.VARCHAR, max_length=30),
            FieldSchema("fetched_at", DataType.VARCHAR, max_length=30),
            # Numeric fields
            FieldSchema("tmdb_year", DataType.INT64),
            FieldSchema("tmdb_season_count", DataType.INT64),
            FieldSchema("tmdb_episode_count", DataType.INT64),
            # Vector field for semantic search
            FieldSchema("text_vector", DataType.FLOAT_VECTOR, dim=384)
        ])
        self._create_collection_if_not_exists("tv_shows", tv_shows_schema)

        # Episodes collection
        episodes_schema = CollectionSchema([
            FieldSchema("id", DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema("tmdb_id", DataType.INT64),
            FieldSchema("season", DataType.INT64),
            FieldSchema("episode", DataType.INT64),
            FieldSchema("abs_episode", DataType.INT64),
            FieldSchema("episode_type", DataType.VARCHAR, max_length=50),
            FieldSchema("episode_id", DataType.INT64),
            FieldSchema("name", DataType.VARCHAR, max_length=255),
            FieldSchema("overview", DataType.VARCHAR, max_length=2048),
            # Store timestamps as strings in ISO format
            FieldSchema("air_date", DataType.VARCHAR, max_length=30),
            FieldSchema("fetched_at", DataType.VARCHAR, max_length=30),
            # Vector field for semantic search
            FieldSchema("text_vector", DataType.FLOAT_VECTOR, dim=384)
        ])
        self._create_collection_if_not_exists("episodes", episodes_schema)

        # Files collections (downloaded, sftp_temp, inventory)
        files_schema = CollectionSchema([
            FieldSchema("id", DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema("name", DataType.VARCHAR, max_length=255),
            FieldSchema("size", DataType.INT64),
            FieldSchema("modified_time", DataType.VARCHAR, max_length=30),
            FieldSchema("path", DataType.VARCHAR, max_length=1024),
            FieldSchema("fetched_at", DataType.VARCHAR, max_length=30),
            FieldSchema("is_dir", DataType.BOOL),
            # Vector field for semantic search
            FieldSchema("text_vector", DataType.FLOAT_VECTOR, dim=384)
        ])
        
        for collection_name in ["downloaded_files", "sftp_temp_files", "anime_tv_inventory"]:
            self._create_collection_if_not_exists(collection_name, files_schema)

        logger.info("Database initialized successfully")

    def add_show(self, show: Any) -> None:
        """Add a show to the database."""
        collection = Collection("tv_shows")
        # Convert show object to dictionary
        show_dict = show.to_dict()
        # Add vector embedding for text fields
        show_dict["text_vector"] = self._get_text_embedding(
            f"{show_dict['sys_name']} {show_dict['tmdb_name']} {show_dict.get('tmdb_overview', '')}"
        )
        collection.insert([show_dict])
        logger.info(f"Inserted show: {show.tmdb_name}")

    def add_episode(self, episode: Any) -> None:
        """Add an episode to the database."""
        collection = Collection("episodes")
        # Convert episode object to dictionary
        episode_dict = episode.to_dict()
        # Add vector embedding for text fields
        episode_dict["text_vector"] = self._get_text_embedding(
            f"{episode_dict['name']} {episode_dict.get('overview', '')}"
        )
        collection.insert([episode_dict])
        logger.info(f"Inserted episode S{episode.season:02d}E{episode.episode:04d} - {episode.name}")

    def add_episodes(self, episodes: List[Any]) -> None:
        """Add multiple episodes to the database."""
        collection = Collection("episodes")
        episode_dicts = []
        for episode in episodes:
            episode_dict = episode.to_dict()
            episode_dict["text_vector"] = self._get_text_embedding(
                f"{episode_dict['name']} {episode_dict.get('overview', '')}"
            )
            episode_dicts.append(episode_dict)
        collection.insert(episode_dicts)
        logger.info(f"Inserted {len(episodes)} episodes.")

    def show_exists(self, name: str) -> bool:
        """Check if a show exists based on name or aliases."""
        collection = Collection("tv_shows")
        # Search by exact match first
        expr = f'sys_name == "{name}" or tmdb_name == "{name}"'
        results = collection.query(expr=expr)
        if results:
            logger.info(f"Show {name} already exists in the database. (Exact Match)")
            return True

        # Search by semantic similarity
        vector = self._get_text_embedding(name)
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = collection.search(
            data=[vector],
            anns_field="text_vector",
            param=search_params,
            limit=5,
            expr=None
        )
        
        if results and results[0].distances[0] < 0.5:  # Threshold for similarity
            logger.info(f"Show {name} already exists in the database. (Semantic Match)")
            return True
            
        return False

    def get_show_by_sys_name(self, sys_name: str) -> Optional[Dict[str, Any]]:
        """Get a show by its system name."""
        collection = Collection("tv_shows")
        expr = f'sys_name == "{sys_name}"'
        results = collection.query(expr=expr)
        if results:
            return results[0]
        return None

    def get_show_by_name_or_alias(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a show by name or alias."""
        collection = Collection("tv_shows")
        # Try exact match first
        expr = f'sys_name == "{name}" or tmdb_name == "{name}"'
        results = collection.query(expr=expr)
        if results:
            logger.info(f"Show {name} found in database. (Exact Match)")
            return results[0]

        # Try semantic search
        vector = self._get_text_embedding(name)
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = collection.search(
            data=[vector],
            anns_field="text_vector",
            param=search_params,
            limit=1,
            expr=None
        )
        
        if results and results[0].distances[0] < 0.5:  # Threshold for similarity
            logger.info(f"Show {name} found in database. (Semantic Match)")
            return results[0].entity
            
        return None

    def get_show_by_tmdb_id(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a show record by TMDB ID."""
        collection = Collection("tv_shows")
        expr = f'tmdb_id == {tmdb_id}'
        results = collection.query(expr=expr)
        if results:
            record = results[0]  # Milvus returns dict-like records
            logger.info(f"Show {record.get('tmdb_name', '')} found in database. (TMDB ID Match)")
            return record
        else:
            logger.info(f"No show found in database for TMDB ID {tmdb_id}")
            return None

    def get_show_by_id(self, show_id: int) -> Optional[Dict[str, Any]]:
        """Get a show by its database ID.
        
        Args:
            show_id: Database ID of the show to retrieve
            
        Returns:
            dict: Show record if found, None otherwise
        """
        collection = Collection("tv_shows")
        expr = f'id == {show_id}'
        results = collection.query(expr=expr)
        
        if results:
            # Convert Milvus result to standard format
            result = results[0]
            return {
                'id': result.get('id'),
                'sys_name': result.get('sys_name'),
                'sys_path': result.get('sys_path'),
                'tmdb_name': result.get('tmdb_name'),
                'aliases': result.get('tmdb_aliases'),
                'tmdb_id': result.get('tmdb_id'),
                'tmdb_first_aired': result.get('tmdb_first_aired'),
                'tmdb_last_aired': result.get('tmdb_last_aired'),
                'tmdb_year': result.get('tmdb_year'),
                'tmdb_overview': result.get('tmdb_overview'),
                'tmdb_season_count': result.get('tmdb_season_count'),
                'tmdb_episode_count': result.get('tmdb_episode_count'),
                'tmdb_episode_groups': result.get('tmdb_episode_groups'),
                'tmdb_episodes_fetched_at': result.get('tmdb_episodes_fetched_at'),
                'tmdb_status': result.get('tmdb_status'),
                'tmdb_external_ids': result.get('tmdb_external_ids'),
                'fetched_at': result.get('fetched_at')
            }
        return None

    def get_all_shows(self) -> List[Dict[str, Any]]:
        """Get all shows from the database."""
        collection = Collection("tv_shows")
        results = collection.query(expr="")
        logger.debug(f"Fetched {len(results)} shows from tv_shows")
        return results

    def episodes_exist(self, tmdb_id: int) -> bool:
        """Check if episodes exist for the given show ID."""
        collection = Collection("episodes")
        expr = f'tmdb_id == {tmdb_id}'
        results = collection.query(expr=expr)
        count = len(results)
        logger.debug(f"Found {count} episodes for tmdb_id={tmdb_id}")
        return count > 0

    def get_episodes_by_tmdb_id(self, tmdb_id: int) -> List[Dict[str, Any]]:
        """Get all episodes for a show by its TMDB ID."""
        collection = Collection("episodes")
        expr = f'tmdb_id == {tmdb_id}'
        results = collection.query(expr=expr)
        logger.debug(f"Fetched {len(results)} episodes for tmdb_id={tmdb_id}")
        return results

    def get_inventory_files(self) -> List[Dict[str, Any]]:
        """Get all inventory files."""
        collection = Collection("anime_tv_inventory")
        results = collection.query(expr="")
        logger.debug(f"Retrieved {len(results)} files from anime_tv_inventory.")
        return results

    def get_downloaded_files(self) -> List[Dict[str, Any]]:
        """Get all downloaded files."""
        collection = Collection("downloaded_files")
        results = collection.query(expr="")
        logger.debug(f"Retrieved {len(results)} files from downloaded_files.")
        return results

    def add_downloaded_files(self, files: List[Dict[str, Any]]) -> None:
        """Add multiple downloaded files to the database."""
        collection = Collection("downloaded_files")
        for file in files:
            file["text_vector"] = self._get_text_embedding(f"{file['name']} {file['path']}")
        collection.insert(files)
        logger.info(f"Inserted {len(files)} records into downloaded_files.")

    def get_sftp_diffs(self) -> List[Dict[str, Any]]:
        """Get differences between SFTP and downloaded files."""
        sftp_collection = Collection("sftp_temp_files")
        downloaded_collection = Collection("downloaded_files")
        
        # Get all SFTP files
        sftp_files = sftp_collection.query(expr="")
        downloaded_files = downloaded_collection.query(expr="")
        
        # Convert to sets for comparison
        sftp_set = {(f["name"], f["size"], f["modified_time"], f["path"], f["is_dir"]) 
                   for f in sftp_files}
        downloaded_set = {(f["name"], f["size"], f["modified_time"], f["path"], f["is_dir"]) 
                         for f in downloaded_files}
        
        # Find differences
        diff_tuples = sftp_set - downloaded_set
        diffs = [
            {
                "name": t[0],
                "size": t[1],
                "modified_time": t[2],
                "path": t[3],
                "is_dir": t[4]
            }
            for t in diff_tuples
        ]
        
        logger.debug(f"SFTP diff found {len(diffs)} new or changed files.")
        return diffs

    def _get_text_embedding(self, text: str) -> List[float]:
        """Get vector embedding for text using a sentence transformer model.
        
        This is a placeholder implementation. In a real implementation,
        you would use a proper sentence transformer model to generate embeddings.
        """
        # Placeholder: Return a random vector of dimension 384
        # In a real implementation, use a proper sentence transformer
        import numpy as np
        return list(np.random.rand(384).astype(float))

    def add_inventory_files(self, files: List[Dict[str, Any]]) -> None:
        """Insert a list of inventory files into the anime_tv_inventory table."""
        collection = Collection("anime_tv_inventory")
        for file in files:
            file["text_vector"] = self._get_text_embedding(f"{file['name']} {file['path']}")
        collection.insert(files)
        logger.info(f"Inserted {len(files)} inventory files into anime_tv_inventory.")

    def add_downloaded_file(self, file: Dict[str, Any]) -> None:
        """Insert a single downloaded file metadata entry into the downloaded_files table."""
        collection = Collection("downloaded_files")
        file["text_vector"] = self._get_text_embedding(f"{file['name']} {file['path']}")
        collection.insert([file])
        logger.debug(f"Inserted downloaded file: {file['name']}")

    def clear_sftp_temp_files(self) -> None:
        """Drop and recreate the sftp_temp_files collection to refresh remote listing."""
        if utility.has_collection("sftp_temp_files"):
            utility.drop_collection("sftp_temp_files")
        
        files_schema = CollectionSchema([
            FieldSchema("id", DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema("name", DataType.VARCHAR, max_length=255),
            FieldSchema("size", DataType.INT64),
            FieldSchema("modified_time", DataType.VARCHAR, max_length=30),
            FieldSchema("path", DataType.VARCHAR, max_length=1024),
            FieldSchema("fetched_at", DataType.VARCHAR, max_length=30),
            FieldSchema("is_dir", DataType.BOOL),
            FieldSchema("text_vector", DataType.FLOAT_VECTOR, dim=384)
        ])
        self._create_collection_if_not_exists("sftp_temp_files", files_schema)
        logger.info("sftp_temp_files collection reset.")

    def clear_downloaded_files(self) -> None:
        """Drop and recreate the downloaded_files collection to refresh local listing."""
        if utility.has_collection("downloaded_files"):
            utility.drop_collection("downloaded_files")
        
        files_schema = CollectionSchema([
            FieldSchema("id", DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema("name", DataType.VARCHAR, max_length=255),
            FieldSchema("size", DataType.INT64),
            FieldSchema("modified_time", DataType.VARCHAR, max_length=30),
            FieldSchema("path", DataType.VARCHAR, max_length=1024),
            FieldSchema("fetched_at", DataType.VARCHAR, max_length=30),
            FieldSchema("is_dir", DataType.BOOL),
            FieldSchema("text_vector", DataType.FLOAT_VECTOR, dim=384)
        ])
        self._create_collection_if_not_exists("downloaded_files", files_schema)
        logger.info("downloaded_files collection reset.")

    def insert_sftp_temp_files(self, entries: List[Dict[str, Any]]) -> None:
        """Insert multiple entries into the sftp_temp_files collection."""
        collection = Collection("sftp_temp_files")
        for entry in entries:
            entry["text_vector"] = self._get_text_embedding(f"{entry['name']} {entry['path']}")
            if isinstance(entry["modified_time"], str):
                entry["modified_time"] = entry["modified_time"]
            else:
                entry["modified_time"] = entry["modified_time"].isoformat()
            if isinstance(entry["fetched_at"], str):
                entry["fetched_at"] = entry["fetched_at"]
            else:
                entry["fetched_at"] = entry["fetched_at"].isoformat()
        collection.insert(entries)
        logger.info(f"Inserted {len(entries)} entries into sftp_temp_files.")

    def get_episodes_by_show_name(self, show_name: str) -> List[Dict[str, Any]]:
        """Return all episodes for the given show name by first resolving the TMDB ID."""
        collection = Collection("tv_shows")
        expr = f'sys_name == "{show_name}"'
        results = collection.query(expr=expr)
        if not results:
            logger.warning(f"No TMDB ID found for show name '{show_name}'")
            return []
        return self.get_episodes_by_tmdb_id(results[0]["tmdb_id"])

    def get_episode_by_absolute_number(self, tmdb_id: int, abs_episode: int) -> Optional[Dict[str, Any]]:
        """Retrieve episode info using tmdb_id and absolute episode number."""
        collection = Collection("episodes")
        expr = f'tmdb_id == {tmdb_id} && abs_episode == {abs_episode}'
        results = collection.query(expr=expr)
        return results[0] if results else None

    def delete_show_and_episodes(self, tmdb_id: int) -> None:
        """Delete a show and all its associated episodes from the database."""
        episodes_collection = Collection("episodes")
        shows_collection = Collection("tv_shows")

        # Delete episodes first
        expr = f'tmdb_id == {tmdb_id}'
        episodes_collection.delete(expr)
        deleted_episodes = episodes_collection.num_entities

        # Delete show
        shows_collection.delete(expr)
        deleted_shows = shows_collection.num_entities

        logger.info(f"Deleted {deleted_episodes} episodes and {deleted_shows} show(s) for tmdb_id={tmdb_id}")

    def copy_sftp_temp_to_downloaded(self) -> None:
        """Copy all records from sftp_temp_files to downloaded_files collection."""
        sftp_collection = Collection("sftp_temp_files")
        downloaded_collection = Collection("downloaded_files")

        # Get all records from sftp_temp_files
        results = sftp_collection.query(expr="")
        if results:
            downloaded_collection.insert(results)
            logger.info(f"Copied {len(results)} records from sftp_temp_files to downloaded_files.")

    def backup_database(self) -> str:
        """
        Creates a backup of the Milvus database by dumping all collections to JSON files.
        The backup is stored in a 'backups/milvus' directory.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        backup_dir = os.path.join("backups", "milvus", f"backup_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)

        try:
            collections = utility.list_collections()
            logger.info(f"Found collections to back up: {collections}")

            for collection_name in collections:
                logger.info(f"Backing up collection: {collection_name}")
                collection = Collection(collection_name)
                collection.load()

                # Query all data from the collection
                results = collection.query(expr="id >= 0", output_fields=["*"])

                backup_file_path = os.path.join(
                    backup_dir, f"{collection_name}.json"
                )
                with open(backup_file_path, "w") as f:
                    json.dump(results, f, indent=4)

                logger.info(
                    f"Collection '{collection_name}' backed up to '{backup_file_path}'"
                )
                collection.release()

            logger.info(f"Milvus database backup completed in: {backup_dir}")
            return backup_dir
        except Exception as e:
            logger.error(f"Milvus backup failed: {e}")
            raise

    def get_show_by_name(self, name: str) -> Optional[Show]:
        # ...
        pass 