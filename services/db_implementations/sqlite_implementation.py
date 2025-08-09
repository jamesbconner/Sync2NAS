# db_implementations/sqlite_service.py
import os
import json
import sqlite3
import datetime
import logging
import shutil
from typing import List, Dict, Any, Optional, Tuple, Union
from contextlib import contextmanager
from models.episode import Episode
from services.db_implementations.db_interface import DatabaseInterface
from models.show import Show
from models.downloaded_file import DownloadedFile, FileStatus

logger = logging.getLogger(__name__)

class SQLiteDBService(DatabaseInterface):
    """
    SQLite implementation of the DatabaseInterface for Sync2NAS.

    Provides methods for managing TV shows, episodes, and file metadata using SQLite as the backend.

    Attributes:
        db_file (str): Path to the SQLite database file.

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
        get_downloaded_files(): Get all downloaded files (legacy view).
        add_downloaded_files(files): Add multiple downloaded files (legacy insert; maps to new schema).
        add_downloaded_file(file): Add a single downloaded file (legacy insert; maps to new schema).
        get_sftp_diffs(): Get differences between SFTP temp listing and downloaded files (by remote_path).
        clear_downloaded_files(): Drop and recreate downloaded_files table.
        clear_sftp_temp_files(): Drop and recreate sftp_temp_files table.
        copy_sftp_temp_to_downloaded(): Copy temp entries into downloaded_files with defaults.
        upsert_downloaded_file(file): Insert or update DownloadedFile by remote_path.
        set_downloaded_file_hash(...): Update hash fields for a downloaded file.
        update_downloaded_file_location(...): Update current/previous path and status.
        update_downloaded_file_location_by_current_path(...): Update by current path.
        mark_downloaded_file_error(...): Mark error status and message.
        get_downloaded_files_by_status(status): List records by status.
        get_downloaded_file_by_remote_path(path): Fetch by remote_path.
        search_downloaded_files(...): Filtered, paginated listing.
        backup_database(): Backup the database.
    """
    
    def __init__(self, db_file: str, read_only: bool = False) -> None:
        """Initialize the repository with a database file path.
        
        Args:
            db_file: Path to the SQLite database file
            read_only: If True, database will be opened in read-only mode
        """
        self.db_file = db_file
        self.read_only = read_only
        self._register_sqlite_datetime_adapters()

    @contextmanager
    def _connection(self):
        """Context manager to get a connection to the database."""
        try:
            if self.read_only:
                # For read-only mode, try URI mode first, fallback to regular mode
                try:
                    uri = f"file:{self.db_file}?mode=ro"
                    conn = sqlite3.connect(uri, detect_types=sqlite3.PARSE_DECLTYPES, timeout=10.0)
                except sqlite3.OperationalError:
                    # Fallback to regular connection for read-only
                    conn = sqlite3.connect(self.db_file, detect_types=sqlite3.PARSE_DECLTYPES, timeout=10.0)
            else:
                conn = sqlite3.connect(self.db_file, detect_types=sqlite3.PARSE_DECLTYPES, timeout=10.0)
            
            try:
                yield conn
                if not self.read_only:
                    conn.commit()
            except sqlite3.Error as e:
                logger.exception(f"Error in database operation: {e}")
                if not self.read_only:
                    conn.rollback()
                raise  # Re-raise the error
            finally:
                conn.close()
        except Exception as e:
            logger.exception(f"Failed to connect to database {self.db_file}: {e}")
            raise

    def __str__(self):
        """Return a string representation of the repository."""
        return f"SQLiteDBService(db_file={self.db_file})"

    @staticmethod
    def _datetime_to_iso(dt):
        """Convert a datetime object to ISO format string."""
        return dt.isoformat()

    @staticmethod
    def _iso_to_datetime(iso_str):
        """Convert an ISO format string to a datetime object."""
        if isinstance(iso_str, bytes):
            try:
                iso_str = iso_str.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("Invalid byte sequence for datetime conversion")
        return datetime.datetime.fromisoformat(iso_str)

    def _register_sqlite_datetime_adapters(self):
        """Register SQLite adapter and converter for datetime handling."""
        try:
            sqlite3.register_adapter(datetime.datetime, self._datetime_to_iso)
            sqlite3.register_converter("DATETIME", self._iso_to_datetime)
        except sqlite3.ProgrammingError as pe:
            logger.exception(f"SQLite adapter registration failed: {pe}")
        except sqlite3.OperationalError as oe:
            logger.exception(f"SQLite converter registration failed: {oe}")
        except sqlite3.Error as e:
            logger.exception(f"Error registering SQLite adapters: {e}")
        except Exception as unk:
            logger.exception(f"Unexpected error occurred while registering SQLite adapters: {unk}")

    def _check_database_path(self):
        """Verify the database file exists and create its directory if needed."""
        logger.debug(f"Resolved DB path: {os.path.abspath(self.db_file)}")
        
        if not os.path.exists(self.db_file):
            logger.exception(f"Database file does not exist: {self.db_file}")
            try:
                os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
                logger.info(f"Created database directory: {os.path.dirname(self.db_file)}")
                return True
            except OSError as ose:
                logger.exception(f"Error creating database directory: {ose}")
                raise
            except Exception as e:
                logger.exception(f"Unexpected error occurred while creating database directory: {e}")
                raise
        return True

    def _create_table_tv_shows(self, conn: sqlite3.Connection) -> None:
        conn.execute('''CREATE TABLE IF NOT EXISTS tv_shows (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            sys_name TEXT NOT NULL,
                            sys_path TEXT NOT NULL,
                            tmdb_name TEXT,
                            tmdb_aliases TEXT,
                            tmdb_id INTEGER,
                            tmdb_first_aired DATETIME,
                            tmdb_last_aired DATETIME,
                            tmdb_year INTEGER,
                            tmdb_overview TEXT,
                            tmdb_season_count INTEGER,
                            tmdb_episode_count INTEGER,
                            tmdb_episode_groups TEXT,  
                            tmdb_episodes_fetched_at DATETIME,
                            tmdb_status TEXT,
                            tmdb_external_ids TEXT,
                            fetched_at DATETIME)''')

    def _create_table_episodes(self, conn: sqlite3.Connection) -> None:
        conn.execute('''CREATE TABLE IF NOT EXISTS episodes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            tmdb_id INTEGER NOT NULL,
                            season INTEGER,
                            episode INTEGER,
                            abs_episode INTEGER,
                            episode_type TEXT,
                            episode_id INTEGER, 
                            air_date DATETIME, 
                            fetched_at DATETIME, 
                            name TEXT, 
                            overview TEXT, 
                            UNIQUE (tmdb_id, season, episode) ON CONFLICT REPLACE,
                            CONSTRAINT FK_episodes_tv_shows FOREIGN KEY (tmdb_id) REFERENCES tv_shows(tmdb_id))''')

    def _create_table_downloaded_files(self, conn: sqlite3.Connection) -> None:
        conn.execute('''CREATE TABLE IF NOT EXISTS downloaded_files (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            path TEXT NOT NULL,
                            remote_path TEXT NOT NULL UNIQUE,
                            current_path TEXT NULL,
                            previous_path TEXT NULL,
                            size INTEGER NOT NULL,
                            modified_time DATETIME NOT NULL,
                            fetched_at DATETIME NOT NULL,
                            is_dir BOOLEAN NOT NULL,
                            status TEXT NOT NULL,
                            file_type TEXT NOT NULL,
                            file_hash_value TEXT NULL,
                            file_hash_algo TEXT NULL,
                            hash_calculated_at DATETIME NULL,
                            show_name TEXT NULL,
                            season INTEGER NULL,
                            episode INTEGER NULL,
                            confidence REAL NULL,
                            reasoning TEXT NULL,
                            tmdb_id INTEGER NULL,
                            routing_attempts INTEGER NOT NULL DEFAULT 0,
                            last_routing_attempt DATETIME NULL,
                            error_message TEXT NULL,
                            metadata TEXT NULL)''')
        conn.execute("CREATE INDEX IF NOT EXISTS idx_downloaded_files_status ON downloaded_files(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_downloaded_files_current_path ON downloaded_files(current_path)")

    def _create_table_sftp_temp_files(self, conn: sqlite3.Connection) -> None:
        conn.execute('''CREATE TABLE IF NOT EXISTS sftp_temp_files (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            size INTEGER NOT NULL,
                            modified_time DATETIME NOT NULL,
                            path TEXT NOT NULL,
                            fetched_at DATETIME NOT NULL,
                            is_dir BOOLEAN NOT NULL)''')

    def _create_table_inventory(self, conn: sqlite3.Connection) -> None:
        conn.execute('''CREATE TABLE IF NOT EXISTS anime_tv_inventory (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            size INTEGER NOT NULL,
                            modified_time DATETIME NOT NULL,
                            path TEXT NOT NULL,
                            fetched_at DATETIME NOT NULL,
                            is_dir BOOLEAN NOT NULL)''')

    def _initialize_database(self):
        """Initialize the database schema by creating necessary tables if they don't exist."""
        _ = self._check_database_path()
        with self._connection() as conn:
            self._create_table_tv_shows(conn)
            self._create_table_episodes(conn)
            self._create_table_downloaded_files(conn)
            self._create_table_sftp_temp_files(conn)
            self._create_table_inventory(conn)
            conn.commit()
            logger.info("Database initialized successfully")
 
    def initialize(self) -> None:
        """Initialize the database schema."""
        if self.read_only:
            logger.info("Skipping database initialization in read-only mode")
            return
        self._initialize_database()
  
    def add_show(self, show) -> None:
        """Add a show to the database."""
        with self._connection() as conn:
            conn.execute('''
                INSERT INTO tv_shows (
                    sys_name, sys_path, tmdb_name, tmdb_aliases, tmdb_id,
                    tmdb_first_aired, tmdb_last_aired, tmdb_year,
                    tmdb_overview, tmdb_season_count, tmdb_episode_count,
                    tmdb_episode_groups, tmdb_episodes_fetched_at, tmdb_status, 
                    tmdb_external_ids, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', show.to_db_tuple())
            conn.commit()
            logger.info(f"Inserted show: {show.tmdb_name}")
    
    def add_episode(self, episode) -> None:
        """Insert a single episode into the episodes table."""
        with self._connection() as conn:
            conn.execute('''
                INSERT INTO episodes (
                    tmdb_id, season, episode, abs_episode, episode_type,
                    episode_id, air_date, fetched_at, name, overview
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', episode.to_db_tuple())
            conn.commit()
            logger.info(f"Inserted episode S{episode.season:02d}E{episode.episode:04d} - {episode.name}")

    def add_episodes(self, episodes: List["Episode"]) -> None:            
        """Insert or update episodes in the database."""
        if not episodes:
            return

        query = """
            INSERT INTO episodes (
                tmdb_id, season, episode, abs_episode,
                episode_type, episode_id, air_date, fetched_at,
                name, overview
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tmdb_id, season, episode) DO UPDATE SET
                abs_episode = excluded.abs_episode,
                episode_type = excluded.episode_type,
                episode_id = excluded.episode_id,
                air_date = excluded.air_date,
                fetched_at = excluded.fetched_at,
                name = excluded.name,
                overview = excluded.overview;
        """

        params = [ep.to_db_tuple() for ep in episodes]

        with self._connection() as conn:
            conn.executemany(query, params)
            conn.commit() 
            logger.info(f"Inserted {len(episodes)} episodes.")
            
        # """Insert multiple episodes into the episodes table."""
        # with self._connection() as conn:
        #     conn.executemany('''
        #         INSERT INTO episodes (
        #             tmdb_id, season, episode, abs_episode, episode_type,
        #             episode_id, air_date, fetched_at, name, overview
        #         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        #     ''', [ep.to_db_tuple() for ep in episodes])
        #     conn.commit()
        #     logger.info(f"Inserted {len(episodes)} episodes.")

    def show_exists(self, name: str) -> bool:
        """Check if a show exists based on sys_name, tmdb_name, or aliases."""
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
        """Retrieve a show record by sys_name."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM tv_shows WHERE LOWER(sys_name) = LOWER(?)", (sys_name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_show_by_name_or_alias(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a show by its name or alias."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tv_shows")
            for row in cursor.fetchall():
                aliases = [a.strip().lower() for a in (row["tmdb_aliases"] or "").split(",") if a.strip()]
                match_candidates = [row["sys_name"].lower(), row["tmdb_name"].lower()] + aliases

                # Check variations
                name_set = {x.strip() for x in set(name.lower().split(','))}
                sys_name_set = {x.strip() for x in set(row["sys_name"].lower().split(','))}
                alias_set = {x.strip() for x in set(aliases)}
                tmdb_name_set = {x.strip() for x in set(row["tmdb_name"].lower().split(','))}
                set_match_candidates = sys_name_set | alias_set | tmdb_name_set                

                if name.lower() in match_candidates:
                    logger.info(f"Show {name} found in database. (Standard Match)")
                    return dict(row)
                
                if name_set.intersection(set_match_candidates) and len(name_set) > 1:
                    logger.info(f"Show {name} found in database. (Set Match)")
                    return dict(row)

        return None

    def get_show_by_tmdb_id(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a show record by TMDB ID."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tv_shows WHERE tmdb_id = ?", (tmdb_id,))
            row = cursor.fetchone()
            
            if row:
                logger.info(f"Show {row['tmdb_name']} found in database. (TMDB ID Match)")
                return dict(row)
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
            cursor = conn.execute('''
                SELECT id, sys_name, sys_path, tmdb_name, tmdb_aliases, tmdb_id,
                       tmdb_first_aired, tmdb_last_aired, tmdb_year, tmdb_overview,
                       tmdb_season_count, tmdb_episode_count, tmdb_episode_groups,
                       tmdb_episodes_fetched_at, tmdb_status, tmdb_external_ids, fetched_at
                FROM tv_shows 
                WHERE id = ?
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
        """Return all shows from the tv_shows table."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tv_shows")
            shows = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Fetched {len(shows)} shows from tv_shows")
            return shows
    
    def episodes_exist(self, tmdb_id: int) -> bool:
        """Check whether episodes already exist for the given TMDB show ID."""
        with self._connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM episodes WHERE tmdb_id = ?", (tmdb_id,))
            count = cursor.fetchone()[0]
            logger.debug(f"Found {count} episodes for tmdb_id={tmdb_id}")
            return count > 0
    
    def get_episodes_by_tmdb_id(self, tmdb_id: int) -> List[Dict[str, Any]]:
        """Return all episodes for the given TMDB ID."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM episodes WHERE tmdb_id = ?", (tmdb_id,))
            episodes = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Fetched {len(episodes)} episodes for tmdb_id={tmdb_id}")
            return episodes

    def get_inventory_files(self) -> List[Dict[str, Any]]:
        """Return a list of all files in the anime_tv_inventory table."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT name, size, modified_time, path, is_dir
                FROM anime_tv_inventory
            """
            cursor = conn.execute(query)
            files = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Retrieved {len(files)} files from anime_tv_inventory.")
            return files
    
    def get_downloaded_files(self) -> List[Dict[str, Any]]:
        """Return a list of all files in the downloaded_files table."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT name, size, modified_time, remote_path, is_dir
                FROM downloaded_files
            """
            cursor = conn.execute(query)
            files = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Retrieved {len(files)} files from downloaded_files.")
            return files
            
    def add_downloaded_files(self, files: List[Dict[str, Any]]) -> None:
        """Insert a list of downloaded file metadata into the downloaded_files table."""
        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO downloaded_files (
                    name, size, modified_time, path, remote_path, is_dir, fetched_at, status, file_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'downloaded', 'unknown')
                """,
                [
                    (
                        f["name"],
                        f["size"],
                        f["modified_time"],
                        f.get("remote_path") or f["path"],
                        f.get("remote_path") or f["path"],
                        f["is_dir"],
                        f["fetched_at"],
                    )
                    for f in files
                ],
            )
            conn.commit()
            logger.info(f"Inserted {len(files)} records into downloaded_files.")
            
    def get_sftp_diffs(self) -> List[Dict[str, Any]]:
        """Return a list of files present in sftp_temp_files but not in downloaded_files."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT name, size, modified_time, path AS remote_path, is_dir
                FROM sftp_temp_files
                EXCEPT
                SELECT name, size, modified_time, remote_path, is_dir
                FROM downloaded_files
            """
            cursor = conn.execute(query)
            diffs = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"SFTP diff found {len(diffs)} new or changed files.")
            return diffs

    def add_inventory_files(self, files: List[Dict[str, Any]]) -> None:
        """Insert a list of inventory files into the anime_tv_inventory table."""
        with self._connection() as conn:
            conn.executemany('''
                INSERT INTO anime_tv_inventory (name, size, modified_time, path, fetched_at, is_dir)
                VALUES (?, ?, ?, ?, ?, ?)
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
            conn.execute(
                """
                INSERT INTO downloaded_files (
                    name, size, modified_time, path, remote_path, is_dir, fetched_at, status, file_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'downloaded', 'unknown')
                """,
                (
                    file["name"],
                    file["size"],
                    file["modified_time"],
                    file.get("remote_path") or file["path"],
                    file.get("remote_path") or file["path"],
                    file["is_dir"],
                    file["fetched_at"],
                ),
            )
            conn.commit()
            logger.debug(f"Inserted downloaded file: {file['name']}")

    def clear_sftp_temp_files(self) -> None:
        """Drop and recreate the sftp_temp_files table to refresh remote listing."""
        with self._connection() as conn:
            conn.execute("DROP TABLE IF EXISTS sftp_temp_files")
            self._create_table_sftp_temp_files(conn)
            conn.commit()
            logger.info("sftp_temp_files table reset.")

    def clear_downloaded_files(self) -> None:
        """Drop and recreate the downloaded_files table to refresh local listing."""
        with self._connection() as conn:
            conn.execute("DROP TABLE IF EXISTS downloaded_files")
            self._create_table_downloaded_files(conn)
            conn.commit()
            logger.info("downloaded_files table reset.")

    def insert_sftp_temp_files(self, entries: List[Dict[str, Any]]) -> None:
        """Insert multiple entries into the sftp_temp_files table."""
        with self._connection() as conn:
            conn.executemany('''
                INSERT INTO sftp_temp_files (
                    name, path, size, modified_time, fetched_at, is_dir
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', [
                (
                    entry["name"],
                    entry.get("remote_path") or entry["path"],
                    entry["size"],
                    entry["modified_time"] if isinstance(entry["modified_time"], str) else entry["modified_time"].isoformat(),
                    entry["fetched_at"] if isinstance(entry["fetched_at"], str) else entry["fetched_at"].isoformat(),
                    int(entry["is_dir"])
                )
                for entry in entries
            ])
            conn.commit()
            logger.info(f"Inserted {len(entries)} entries into sftp_temp_files.")

    def get_episodes_by_show_name(self, show_name: str) -> List[Dict[str, Any]]:
        """Return all episodes for the given show name by first resolving the TMDB ID."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT tmdb_id FROM tv_shows WHERE sys_name = ?", (show_name,))
            row = cursor.fetchone()
            if not row:
                logger.warning(f"No TMDB ID found for show name '{show_name}'")
                return []
            return self.get_episodes_by_tmdb_id(row["tmdb_id"])

    def get_episode_by_absolute_number(self, tmdb_id: int, abs_episode: int) -> Optional[Dict[str, Any]]:
        """Retrieve episode info using tmdb_id and absolute episode number."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM episodes
                WHERE tmdb_id = ? AND abs_episode = ?
            """, (tmdb_id, abs_episode))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_show_and_episodes(self, tmdb_id: int) -> None:
        """Delete a show and all its associated episodes from the database."""
        with self._connection() as conn:
            cursor = conn.cursor()

            # Delete episodes first due to foreign key constraint
            cursor.execute("DELETE FROM episodes WHERE tmdb_id = ?", (tmdb_id,))
            deleted_episodes = cursor.rowcount

            # Delete show from tv_shows
            cursor.execute("DELETE FROM tv_shows WHERE tmdb_id = ?", (tmdb_id,))
            deleted_shows = cursor.rowcount

            conn.commit()
            logger.info(f"Deleted {deleted_episodes} episodes and {deleted_shows} show(s) for tmdb_id={tmdb_id}")

    def get_sftp_diffs(self) -> List[Dict[str, Any]]:
        """Get differences between SFTP temp listing and new downloaded_files by remote_path."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT s.name, s.size, s.modified_time, s.path, s.is_dir
                FROM sftp_temp_files s
                LEFT JOIN downloaded_files d ON s.path = d.remote_path
                WHERE d.id IS NULL
            """
            cursor = conn.execute(query)
            diffs = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Found {len(diffs)} differences between SFTP and downloaded files.")
            return diffs

    def copy_sftp_temp_to_downloaded(self) -> None:
        """Copy all records from sftp_temp_files to downloaded_files."""
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO downloaded_files (
                    name, size, modified_time, path, remote_path, fetched_at, is_dir, status, file_type
                )
                SELECT name, size, modified_time, path, path, fetched_at, is_dir, 'downloaded', 'unknown'
                FROM sftp_temp_files
            """)
            conn.commit()
            logger.info("Copied sftp_temp_files to downloaded_files.")

    def is_read_only(self) -> bool:
        """Check if database is in read-only mode."""
        return self.read_only

    def backup_database(self) -> str:
        """
        Creates a backup of the SQLite database file.
        The backup is stored in a 'backups/sqlite' directory relative to the db file path,
        with a timestamp in the filename.
        """
        if not self.db_file or not os.path.exists(self.db_file):
            raise FileNotFoundError("Database file not found.")

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        db_dir = os.path.dirname(self.db_file)
        backup_dir = os.path.join(db_dir, "..", "backups", "sqlite")
        os.makedirs(backup_dir, exist_ok=True)

        db_filename = os.path.basename(self.db_file)
        backup_filename = f"{os.path.splitext(db_filename)[0]}_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)

        shutil.copy2(self.db_file, backup_path)
        logger.info(f"SQLite database backed up to {backup_path}")
        return backup_path

    # --------------------- DownloadedFile methods ---------------------
    def _initialize_downloaded_files(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS downloaded_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    remote_path TEXT NOT NULL UNIQUE,
                    current_path TEXT NULL,
                    previous_path TEXT NULL,
                    size INTEGER NOT NULL,
                    modified_time DATETIME NOT NULL,
                    fetched_at DATETIME NOT NULL,
                    is_dir BOOLEAN NOT NULL,
                    status TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_hash_value TEXT NULL,
                    file_hash_algo TEXT NULL,
                    hash_calculated_at DATETIME NULL,
                    show_name TEXT NULL,
                    season INTEGER NULL,
                    episode INTEGER NULL,
                    confidence REAL NULL,
                    reasoning TEXT NULL,
                    tmdb_id INTEGER NULL,
                    routing_attempts INTEGER NOT NULL DEFAULT 0,
                    last_routing_attempt DATETIME NULL,
                    error_message TEXT NULL,
                    metadata TEXT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_downloaded_files_status ON downloaded_files(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_downloaded_files_current_path ON downloaded_files(current_path)"
            )

    def _df_row_to_model(self, row: sqlite3.Row) -> DownloadedFile:
        return DownloadedFile(
            id=row["id"],
            name=row["name"],
            remote_path=row["remote_path"],
            current_path=row["current_path"],
            previous_path=row["previous_path"],
            size=row["size"],
            modified_time=row["modified_time"],
            fetched_at=row["fetched_at"],
            is_dir=bool(row["is_dir"]),
            status=FileStatus(row["status"]),
            file_hash=row["file_hash_value"],
            file_hash_algo=row["file_hash_algo"],
            hash_calculated_at=row["hash_calculated_at"],
            show_name=row["show_name"],
            season=row["season"],
            episode=row["episode"],
            confidence=row["confidence"],
            reasoning=row["reasoning"],
            tmdb_id=row["tmdb_id"],
            routing_attempts=row["routing_attempts"],
            last_routing_attempt=row["last_routing_attempt"],
            error_message=row["error_message"],
        )

    def upsert_downloaded_file(self, file: DownloadedFile) -> DownloadedFile:
        remote_path = file.remote_path
        row = (
            file.name,
            file.remote_path,  # path
            remote_path,
            file.current_path,
            getattr(file, "previous_path", None),
            file.size,
            file.modified_time,
            file.fetched_at,
            int(file.is_dir),
            file.status.value,
            file.file_type.value,
            file.file_hash,
            (file.file_hash_algo if file.file_hash_algo is not None else ("CRC32" if file.file_hash and len(file.file_hash) == 8 else None)),
            getattr(file, "hash_calculated_at", None),
            file.show_name,
            file.season,
            file.episode,
            file.confidence,
            file.reasoning,
            file.tmdb_id,
            file.routing_attempts,
            file.last_routing_attempt,
            file.error_message,
            json.dumps(file.metadata) if file.metadata is not None else None,
        )
        with self._connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO downloaded_files (
                    name, path, remote_path, current_path, previous_path, size, modified_time, fetched_at, is_dir,
                    status, file_type, file_hash_value, file_hash_algo, hash_calculated_at, show_name, season,
                    episode, confidence, reasoning, tmdb_id, routing_attempts, last_routing_attempt, error_message, metadata
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(remote_path) DO UPDATE SET
                    name=excluded.name,
                    path=excluded.path,
                    current_path=excluded.current_path,
                    previous_path=excluded.previous_path,
                    size=excluded.size,
                    modified_time=excluded.modified_time,
                    fetched_at=excluded.fetched_at,
                    is_dir=excluded.is_dir,
                    status=excluded.status,
                    file_type=excluded.file_type,
                    file_hash_value=COALESCE(excluded.file_hash_value, downloaded_files.file_hash_value),
                    file_hash_algo=COALESCE(excluded.file_hash_algo, downloaded_files.file_hash_algo),
                    show_name=excluded.show_name,
                    season=excluded.season,
                    episode=excluded.episode,
                    confidence=excluded.confidence,
                    reasoning=excluded.reasoning,
                    tmdb_id=excluded.tmdb_id,
                    routing_attempts=excluded.routing_attempts,
                    last_routing_attempt=excluded.last_routing_attempt,
                    error_message=excluded.error_message,
                    metadata=excluded.metadata
                """,
                row,
            )
            file_id = cur.lastrowid
            if not file_id:
                cur2 = conn.execute(
                    "SELECT id FROM downloaded_files WHERE remote_path = ?",
                    (remote_path,),
                )
                res = cur2.fetchone()
                if res:
                    file_id = res[0]
            file.id = file_id
            return file

    def set_downloaded_file_hash(self, file_id: int, algo: str, value: str, calculated_at: Optional[datetime.datetime] = None) -> None:
        if calculated_at is None:
            calculated_at = datetime.datetime.now()
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE downloaded_files
                SET file_hash_value = ?, file_hash_algo = ?, hash_calculated_at = ?
                WHERE id = ?
                """,
                (value, algo, calculated_at, file_id),
            )

    def update_downloaded_file_location(self, file_id: int, new_path: str, new_status: FileStatus = FileStatus.ROUTED, routed_at: Optional[datetime.datetime] = None) -> None:
        if routed_at is None:
            routed_at = datetime.datetime.now()
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE downloaded_files
                SET previous_path = current_path,
                    current_path = ?,
                    status = ?,
                    routing_attempts = routing_attempts + 1,
                    last_routing_attempt = ?
                WHERE id = ?
                """,
                (new_path, new_status.value, routed_at, file_id),
            )

    def update_downloaded_file_location_by_current_path(self, current_path: str, new_path: str, new_status: FileStatus = FileStatus.ROUTED, routed_at: Optional[datetime.datetime] = None) -> None:
        if routed_at is None:
            routed_at = datetime.datetime.now()
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE downloaded_files
                SET previous_path = current_path,
                    current_path = ?,
                    status = ?,
                    routing_attempts = routing_attempts + 1,
                    last_routing_attempt = ?
                WHERE current_path = ?
                """,
                (new_path, new_status.value, routed_at, current_path),
            )

    def mark_downloaded_file_error(self, file_id: int, message: str) -> None:
        now = datetime.datetime.now()
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE downloaded_files
                SET status = ?, error_message = ?, last_routing_attempt = ?
                WHERE id = ?
                """,
                (FileStatus.ERROR.value, message, now, file_id),
            )

    def update_downloaded_file_status(self, file_id: int, new_status: FileStatus, error_message: Optional[str] = None) -> None:
        with self._connection() as conn:
            if error_message is None:
                conn.execute(
                    "UPDATE downloaded_files SET status = ? WHERE id = ?",
                    (new_status.value, file_id),
                )
            else:
                conn.execute(
                    "UPDATE downloaded_files SET status = ?, error_message = ? WHERE id = ?",
                    (new_status.value, error_message, file_id),
                )

    def get_downloaded_files_by_status(self, status: FileStatus) -> List[DownloadedFile]:
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM downloaded_files WHERE status = ?",
                (status.value,),
            )
            return [self._df_row_to_model(r) for r in cur.fetchall()]

    def get_downloaded_file_by_remote_path(self, remote_path: str) -> Optional[DownloadedFile]:
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM downloaded_files WHERE remote_path = ?",
                (remote_path,),
            )
            row = cur.fetchone()
            return self._df_row_to_model(row) if row else None

    def get_downloaded_file_by_id(self, file_id: int) -> Optional[DownloadedFile]:
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM downloaded_files WHERE id = ?",
                (file_id,),
            )
            row = cur.fetchone()
            return self._df_row_to_model(row) if row else None

    def search_downloaded_files(
        self,
        *,
        status: Optional[FileStatus] = None,
        file_type: Optional[str] = None,
        q: Optional[str] = None,
        tmdb_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "modified_time",
        sort_order: str = "desc",
    ) -> Tuple[List[DownloadedFile], int]:
        where = []
        params: list = []
        if status:
            where.append("status = ?")
            params.append(status.value)
        if file_type:
            where.append("file_type = ?")
            params.append(file_type)
        if tmdb_id is not None:
            where.append("tmdb_id = ?")
            params.append(tmdb_id)
        if q:
            where.append("(name LIKE ? OR remote_path LIKE ? OR current_path LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like, like])

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        sort_order = "DESC" if sort_order.lower() == "desc" else "ASC"
        allowed_sort = {"modified_time", "fetched_at", "name", "size"}
        sort_by = sort_by if sort_by in allowed_sort else "modified_time"

        limit = max(1, min(page_size, 200))
        offset = max(0, (max(1, page) - 1) * limit)

        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            count_cur = conn.execute(
                f"SELECT COUNT(*) as c FROM downloaded_files {where_sql}", params
            )
            total = count_cur.fetchone()[0]

            page_cur = conn.execute(
                f"SELECT * FROM downloaded_files {where_sql} ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?",
                params + [limit, offset],
            )
            items = [self._df_row_to_model(r) for r in page_cur.fetchall()]
            return items, int(total)