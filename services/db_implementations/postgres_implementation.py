import os
import json
import psycopg2
import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from contextlib import contextmanager
from models.episode import Episode
from models.show import Show
from services.db_implementations.db_interface import DatabaseInterface
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logger = logging.getLogger(__name__)

class PostgresDBService(DatabaseInterface):
    """
    PostgreSQL implementation of the DatabaseInterface for Sync2NAS.

    Provides methods for managing TV shows, episodes, and file metadata using PostgreSQL as the backend.

    Attributes:
        connection_string (str): PostgreSQL connection string.

    Methods:
        initialize(): Initialize the database schema.
        add_show(show): Add a show to the database.
        add_episode(episode): Add an episode to the database.
        add_episodes(episodes): Add multiple episodes to the database.
        show_exists(name): Check if a show exists.
        get_show_by_sys_name(sys_name): Get a show by its system name.
        get_show_by_name_or_alias(name): Get a show by name or alias.
        get_show_by_tmdb_id(tmdb_id): Get a show by TMDB ID.
        get_show_by_id(show_id): Get a show by database ID.
        get_all_shows(): Get all shows.
        episodes_exist(tmdb_id): Check if episodes exist for a show.
        get_episodes_by_tmdb_id(tmdb_id): Get all episodes for a show.
        get_inventory_files(): Get all inventory files.
        get_downloaded_files(): Get all downloaded files.
        add_downloaded_files(files): Add multiple downloaded files.
        get_sftp_diffs(): Get differences between SFTP and downloaded files.
        backup_database(): Backup the database.
    """
    
    def __init__(self, connection_string: str, read_only: bool = False) -> None:
        """Initialize the repository with a connection string.
        
        Args:
            connection_string: PostgreSQL connection string
            read_only: If True, database will be in read-only mode (TODO: implement read-only user)
        """
        self.connection_string = connection_string
        self.read_only = read_only

    @contextmanager
    def _connection(self):
        """Context manager to get a connection to the database."""
        conn = psycopg2.connect(self.connection_string)
        try:
            yield conn
            conn.commit()
        except psycopg2.Error as e:
            logger.exception(f"Error in database operation: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Initialize the database schema."""
        with self._connection() as conn:
            cursor = conn.cursor()
            # Create tables
            cursor.execute('''CREATE TABLE IF NOT EXISTS tv_shows (
                id SERIAL PRIMARY KEY,
                sys_name TEXT NOT NULL,
                sys_path TEXT NOT NULL,
                tmdb_name TEXT,
                tmdb_aliases TEXT,
                tmdb_id INTEGER,
                tmdb_first_aired TIMESTAMP,
                tmdb_last_aired TIMESTAMP,
                tmdb_year INTEGER,
                tmdb_overview TEXT,
                tmdb_season_count INTEGER,
                tmdb_episode_count INTEGER,
                tmdb_episode_groups TEXT,
                tmdb_episodes_fetched_at TIMESTAMP,
                tmdb_status TEXT,
                tmdb_external_ids TEXT,
                fetched_at TIMESTAMP
            )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS episodes (
                id SERIAL PRIMARY KEY,
                tmdb_id INTEGER NOT NULL,
                season INTEGER,
                episode INTEGER,
                abs_episode INTEGER,
                episode_type TEXT,
                episode_id INTEGER,
                air_date TIMESTAMP,
                fetched_at TIMESTAMP,
                name TEXT,
                overview TEXT,
                CONSTRAINT FK_episodes_tv_shows FOREIGN KEY (tmdb_id) REFERENCES tv_shows(tmdb_id)
            )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS downloaded_files (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                size BIGINT NOT NULL,
                modified_time TIMESTAMP NOT NULL,
                path TEXT NOT NULL,
                fetched_at TIMESTAMP NOT NULL,
                is_dir BOOLEAN NOT NULL
            )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS sftp_temp_files (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                size BIGINT NOT NULL,
                modified_time TIMESTAMP NOT NULL,
                path TEXT NOT NULL,
                fetched_at TIMESTAMP NOT NULL,
                is_dir BOOLEAN NOT NULL
            )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS anime_tv_inventory (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                size BIGINT NOT NULL,
                modified_time TIMESTAMP NOT NULL,
                path TEXT NOT NULL,
                fetched_at TIMESTAMP NOT NULL,
                is_dir BOOLEAN NOT NULL
            )''')
            
            cursor.execute('''CREATE UNIQUE INDEX idx_episodes_unique ON episodes (tmdb_id, season, episode)''')
            conn.commit()
            logger.info("Database initialized successfully")

    def add_show(self, show: Any) -> None:
        """Add a show to the database."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tv_shows (
                    sys_name, sys_path, tmdb_name, tmdb_aliases, tmdb_id,
                    tmdb_first_aired, tmdb_last_aired, tmdb_year,
                    tmdb_overview, tmdb_season_count, tmdb_episode_count,
                    tmdb_episode_groups, tmdb_episodes_fetched_at, tmdb_status,
                    tmdb_external_ids, fetched_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', show.to_db_tuple())
            conn.commit()
            logger.info(f"Inserted show: {show.tmdb_name}")

    def add_episode(self, episode: Any) -> None:
        """Add an episode to the database."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO episodes (
                    tmdb_id, season, episode, abs_episode, episode_type,
                    episode_id, air_date, fetched_at, name, overview
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', episode.to_db_tuple())
            conn.commit()
            logger.info(f"Inserted episode S{episode.season:02d}E{episode.episode:04d} - {episode.name}")

    def add_episodes(self, episodes: List[Any]) -> None:
        """Insert or update episodes in the database."""
        if not episodes:
            return

        query = """
            INSERT INTO episodes (
                tmdb_id, season, episode, abs_episode,
                episode_type, episode_id, air_date, fetched_at,
                name, overview
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tmdb_id, season, episode) DO UPDATE SET
                abs_episode = EXCLUDED.abs_episode,
                episode_type = EXCLUDED.episode_type,
                episode_id = EXCLUDED.episode_id,
                air_date = EXCLUDED.air_date,
                fetched_at = EXCLUDED.fetched_at,
                name = EXCLUDED.name,
                overview = EXCLUDED.overview;
        """

        params = [ep.to_db_tuple() for ep in episodes]

        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, params)
                conn.commit()
                logger.info(f"Inserted {len(episodes)} episodes.")

    def show_exists(self, name: str) -> bool:
        """Check if a show exists based on name or aliases."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT sys_name, tmdb_name, tmdb_aliases FROM tv_shows')
            for row in cursor.fetchall():
                sys_name, tmdb_name, tmdb_aliases = row
                aliases = [a.strip().lower() for a in (tmdb_aliases or "").split(",") if a.strip()]
                match_candidates = [sys_name.lower(), tmdb_name.lower()] + aliases

                # Check variations
                name_set = {x.strip() for x in set(name.lower().split(','))}
                sys_name_set = {x.strip() for x in set(sys_name.lower().split(','))}
                alias_set = {x.strip() for x in set(aliases)}
                tmdb_name_set = {x.strip() for x in set(tmdb_name.lower().split(','))}
                set_match_candidates = sys_name_set | alias_set | tmdb_name_set
                
                if name.lower() in match_candidates:
                    logger.info(f"Show {name} already exists in the database. (Standard Match)")
                    return True
                
                if name_set.intersection(set_match_candidates) and len(name_set) > 1:
                    logger.info(f"Show {name} already exists in the database. (Set Match)")
                    return True
        return False

    def get_show_by_sys_name(self, sys_name: str) -> Optional[Dict[str, Any]]:
        """Get a show by its system name."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tv_shows WHERE LOWER(sys_name) = LOWER(%s)", (sys_name,)
            )
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None

    def get_show_by_name_or_alias(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a show by name or alias."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tv_shows")
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                aliases = [a.strip().lower() for a in (row_dict["tmdb_aliases"] or "").split(",") if a.strip()]
                match_candidates = [row_dict["sys_name"].lower(), row_dict["tmdb_name"].lower()] + aliases

                name_set = {x.strip() for x in set(name.lower().split(','))}
                sys_name_set = {x.strip() for x in set(row_dict["sys_name"].lower().split(','))}
                alias_set = {x.strip() for x in set(aliases)}
                tmdb_name_set = {x.strip() for x in set(row_dict["tmdb_name"].lower().split(','))}
                set_match_candidates = sys_name_set | alias_set | tmdb_name_set

                if name.lower() in match_candidates:
                    logger.info(f"Show {name} found in database. (Standard Match)")
                    return row_dict
                
                if name_set.intersection(set_match_candidates) and len(name_set) > 1:
                    logger.info(f"Show {name} found in database. (Set Match)")
                    return row_dict
        return None

    def get_show_by_tmdb_id(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a show record by TMDB ID."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tv_shows WHERE tmdb_id = %s", (tmdb_id,))
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            
            if row:
                record = dict(zip(columns, row))
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
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, sys_name, sys_path, tmdb_name, tmdb_aliases, tmdb_id,
                       tmdb_first_aired, tmdb_last_aired, tmdb_year, tmdb_overview,
                       tmdb_season_count, tmdb_episode_count, tmdb_episode_groups,
                       tmdb_episodes_fetched_at, tmdb_status, tmdb_external_ids, fetched_at
                FROM tv_shows 
                WHERE id = %s
            ''', (show_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'sys_name': row[1],
                    'sys_path': row[2],
                    'tmdb_name': row[3],
                    'aliases': row[4],
                    'tmdb_id': row[5],
                    'tmdb_first_aired': row[6],
                    'tmdb_last_aired': row[7],
                    'tmdb_year': row[8],
                    'tmdb_overview': row[9],
                    'tmdb_season_count': row[10],
                    'tmdb_episode_count': row[11],
                    'tmdb_episode_groups': row[12],
                    'tmdb_episodes_fetched_at': row[13],
                    'tmdb_status': row[14],
                    'tmdb_external_ids': row[15],
                    'fetched_at': row[16]
                }
            return None

    def get_all_shows(self) -> List[Dict[str, Any]]:
        """Get all shows from the database."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tv_shows")
            columns = [desc[0] for desc in cursor.description]
            shows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            logger.debug(f"Fetched {len(shows)} shows from tv_shows")
            return shows

    def episodes_exist(self, tmdb_id: int) -> bool:
        """Check if episodes exist for the given show ID."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM episodes WHERE tmdb_id = %s", (tmdb_id,))
            count = cursor.fetchone()[0]
            logger.debug(f"Found {count} episodes for tmdb_id={tmdb_id}")
            return count > 0

    def get_episodes_by_tmdb_id(self, tmdb_id: int) -> List[Dict[str, Any]]:
        """Get all episodes for a show by its TMDB ID."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM episodes WHERE tmdb_id = %s", (tmdb_id,))
            columns = [desc[0] for desc in cursor.description]
            episodes = [dict(zip(columns, row)) for row in cursor.fetchall()]
            logger.debug(f"Fetched {len(episodes)} episodes for tmdb_id={tmdb_id}")
            return episodes

    def get_inventory_files(self) -> List[Dict[str, Any]]:
        """Get all inventory files."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, size, modified_time, path, is_dir
                FROM anime_tv_inventory
            """)
            columns = [desc[0] for desc in cursor.description]
            files = [dict(zip(columns, row)) for row in cursor.fetchall()]
            logger.debug(f"Retrieved {len(files)} files from anime_tv_inventory.")
            return files

    def get_downloaded_files(self) -> List[Dict[str, Any]]:
        """Get all downloaded files."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, size, modified_time, path, is_dir
                FROM downloaded_files
            """)
            columns = [desc[0] for desc in cursor.description]
            files = [dict(zip(columns, row)) for row in cursor.fetchall()]
            logger.debug(f"Retrieved {len(files)} files from downloaded_files.")
            return files

    def add_downloaded_files(self, files: List[Dict[str, Any]]) -> None:
        """Add multiple downloaded files to the database."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO downloaded_files (
                    name, size, modified_time, path, is_dir, fetched_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, [
                (
                    f["name"],
                    f["size"],
                    f["modified_time"],
                    f["path"],
                    f["is_dir"],
                    f["fetched_at"],
                )
                for f in files
            ])
            conn.commit()
            logger.info(f"Inserted {len(files)} records into downloaded_files.")

    def get_sftp_diffs(self) -> List[Dict[str, Any]]:
        """Get differences between SFTP and downloaded files."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, size, modified_time, path, is_dir
                FROM sftp_temp_files
                EXCEPT
                SELECT name, size, modified_time, path, is_dir
                FROM downloaded_files
            """)
            columns = [desc[0] for desc in cursor.description]
            diffs = [dict(zip(columns, row)) for row in cursor.fetchall()]
            logger.debug(f"SFTP diff found {len(diffs)} new or changed files.")
            return diffs

    def add_inventory_files(self, files: List[Dict[str, Any]]) -> None:
        """Insert a list of inventory files into the anime_tv_inventory table."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO anime_tv_inventory (name, size, modified_time, path, fetched_at, is_dir)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''',
            [
                (f["name"], f["size"], f["modified_time"], f["path"], f["fetched_at"], f["is_dir"])
                for f in files
            ])
            conn.commit()
            logger.info(f"Inserted {len(files)} inventory files into anime_tv_inventory.")

    def add_downloaded_file(self, file: Dict[str, Any]) -> None:
        """Insert a single downloaded file metadata entry into the downloaded_files table."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO downloaded_files (
                    name, size, modified_time, path, is_dir, fetched_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    file["name"],
                    file["size"],
                    file["modified_time"],
                    file["path"],
                    file["is_dir"],
                    file["fetched_at"],
                ),
            )
            conn.commit()
            logger.debug(f"Inserted downloaded file: {file['name']}")

    def clear_sftp_temp_files(self) -> None:
        """Drop and recreate the sftp_temp_files table to refresh remote listing."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS sftp_temp_files")
            cursor.execute('''CREATE TABLE IF NOT EXISTS sftp_temp_files (
                                id SERIAL PRIMARY KEY,
                                name TEXT NOT NULL,
                                size BIGINT NOT NULL,
                                modified_time TIMESTAMP NOT NULL,
                                path TEXT NOT NULL,
                                fetched_at TIMESTAMP NOT NULL,
                                is_dir BOOLEAN NOT NULL)''')
            conn.commit()
            logger.info("sftp_temp_files table reset.")

    def clear_downloaded_files(self) -> None:
        """Drop and recreate the downloaded_files table to refresh local listing."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS downloaded_files")
            cursor.execute('''CREATE TABLE IF NOT EXISTS downloaded_files (
                                id SERIAL PRIMARY KEY,
                                name TEXT NOT NULL,
                                size BIGINT NOT NULL,
                                modified_time TIMESTAMP NOT NULL,
                                path TEXT NOT NULL,
                                fetched_at TIMESTAMP NOT NULL,
                                is_dir BOOLEAN NOT NULL)''')
            conn.commit()
            logger.info("downloaded_files table reset.")

    def insert_sftp_temp_files(self, entries: List[Dict[str, Any]]) -> None:
        """Insert multiple entries into the sftp_temp_files table."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO sftp_temp_files (
                    name, path, size, modified_time, fetched_at, is_dir
                ) VALUES (%s, %s, %s, %s, %s, %s)
            ''', [
                (
                    entry["name"],
                    entry["path"],
                    entry["size"],
                    entry["modified_time"] if isinstance(entry["modified_time"], str) else entry["modified_time"].isoformat(),
                    entry["fetched_at"] if isinstance(entry["fetched_at"], str) else entry["fetched_at"].isoformat(),
                    entry["is_dir"]
                )
                for entry in entries
            ])
            conn.commit()
            logger.info(f"Inserted {len(entries)} entries into sftp_temp_files.")

    def get_episodes_by_show_name(self, show_name: str) -> List[Dict[str, Any]]:
        """Return all episodes for the given show name by first resolving the TMDB ID."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tmdb_id FROM tv_shows WHERE sys_name = %s", (show_name,))
            row = cursor.fetchone()
            if not row:
                logger.warning(f"No TMDB ID found for show name '{show_name}'")
                return []
            return self.get_episodes_by_tmdb_id(row[0])

    def get_episode_by_absolute_number(self, tmdb_id: int, abs_episode: int) -> Optional[Dict[str, Any]]:
        """Retrieve episode info using tmdb_id and absolute episode number."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM episodes
                WHERE tmdb_id = %s AND abs_episode = %s
            """, (tmdb_id, abs_episode))
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None

    def delete_show_and_episodes(self, tmdb_id: int) -> None:
        """Delete a show and all its associated episodes from the database."""
        with self._connection() as conn:
            cursor = conn.cursor()

            # Delete episodes first due to foreign key constraint
            cursor.execute("DELETE FROM episodes WHERE tmdb_id = %s", (tmdb_id,))
            deleted_episodes = cursor.rowcount

            # Delete show from tv_shows
            cursor.execute("DELETE FROM tv_shows WHERE tmdb_id = %s", (tmdb_id,))
            deleted_shows = cursor.rowcount

            conn.commit()
            logger.info(f"Deleted {deleted_episodes} episodes and {deleted_shows} show(s) for tmdb_id={tmdb_id}")

    def copy_sftp_temp_to_downloaded(self) -> None:
        """Copy all records from sftp_temp_files to downloaded_files."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO downloaded_files (name, size, modified_time, path, fetched_at, is_dir)
                SELECT name, size, modified_time, path, fetched_at, is_dir
                FROM sftp_temp_files
            """)
            conn.commit()
            logger.info("Copied sftp_temp_files to downloaded_files.")

    def backup_database(self) -> str:
        """
        Creates a backup of the PostgreSQL database by creating a new database
        with a timestamp in its name and copying the contents.
        """
        source_db_name = self.conn_params.get("dbname")
        if not source_db_name:
            raise ValueError("Database name not configured.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        backup_db_name = f"{source_db_name}_backup_{timestamp}"

        conn_params_maintenance = self.conn_params.copy()
        conn_params_maintenance["dbname"] = "postgres"  # Connect to maintenance db

        conn = None
        try:
            conn = psycopg2.connect(**conn_params_maintenance)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Check if role has CREATEDB privilege
            cursor.execute(
                "SELECT rolcreatedb FROM pg_roles WHERE rolname = %s;",
                (self.conn_params.get("user"),),
            )
            can_create_db = cursor.fetchone()

            if not can_create_db or not can_create_db[0]:
                raise PermissionError(
                    f"User '{self.conn_params.get('user')}' does not have CREATEDB privilege."
                )

            logger.info(f"Creating backup database: {backup_db_name}")
            cursor.execute(
                f'CREATE DATABASE "{backup_db_name}" WITH TEMPLATE "{source_db_name}" OWNER "{self.conn_params.get("user")}";'
            )
            logger.info(
                f"PostgreSQL database '{source_db_name}' backed up to '{backup_db_name}'"
            )
            cursor.close()
            return backup_db_name
        except Exception as e:
            logger.exception(f"PostgreSQL backup failed: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_show_by_name(self, name: str) -> Optional[Show]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tv_shows WHERE LOWER(sys_name) = LOWER(%s) OR LOWER(tmdb_name) = LOWER(%s)", (name, name))
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            if row:
                show_dict = dict(zip(columns, row))
                return Show(**show_dict)
            else:
                return None

    def is_read_only(self) -> bool:
        """Check if database is in read-only mode.
        
        TODO: Implement read-only user creation and connection string modification
        to achieve true read-only access for PostgreSQL.
        """
        return self.read_only 