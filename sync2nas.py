import os
import re
import shutil
import configparser
import argparse
import sqlite3
import paramiko
import datetime
import stat
import logging
import json
import posixpath
from argparse import Namespace
from typing import List, Dict, Tuple, TypedDict, Any
import tvdb_v4_official as tvdb

############################
##### Setup Script Opt #####
############################
# Encoding constant
UTF_8_ENCODING = "utf-8"

# Setup SQLite
def datetime_to_iso(dt):
    """Convert a datetime object to ISO format string."""
    return dt.isoformat()

def iso_to_datetime(iso_str):
    """Convert an ISO format string to a datetime object."""
    if isinstance(iso_str, bytes):
        iso_str = iso_str.decode(UTF_8_ENCODING)
    return datetime.datetime.fromisoformat(iso_str)

def register_sqlite_datetime_adapters():
    """Register SQLite adapter and converter for datetime handling."""
    sqlite3.register_adapter(datetime.datetime, datetime_to_iso)
    sqlite3.register_converter("DATETIME", iso_to_datetime)

# Register adapters and converters
register_sqlite_datetime_adapters()

# Setup Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set initially to debug; actual output will be controlled by handler.

def setup_logging(verbose: bool):
    """Configures logging based on verbosity."""
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    if verbose:
        handler.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)

    logger.addHandler(handler)


############################
###### SFTP Functions ######
############################
def _connect_sftp(host, port, username, key_path):
    """Sets up and returns an SFTP connection."""
    try:
        logger.debug(f"Connecting to SFTP server: {host}:{port}")
        key = paramiko.RSAKey(filename=key_path)
        transport = paramiko.Transport((host, port))
        transport.connect(username=username, pkey=key)
        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp, transport
    except Exception as e:
        logger.error(f"Error connecting to SFTP server: {e}")
        return None, None

def list_sftp_files(remote_path, sftp=None, cuttime=5, cutsize=0, recursive=False):
    file_list = []
    excluded_extensions = {"jpg", "jpeg", "png", "gif", "bmp", "nfo", "sfv"}
    excluded_keywords = {"screens", "sample"}
    cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=cuttime)
    cutoff_size = cutsize

    try:
        # Setup SFTP object if not exists
        if not recursive:
            logger.debug(f"Establishing SFTP connection for path: {remote_path}")
            sftp, transport = _connect_sftp(SFTP_HOST, SFTP_PORT, SFTP_USERNAME, SSH_KEY_PATH)

        for file_attr in sftp.listdir_attr(remote_path):
            file_name = file_attr.filename
            file_path = posixpath.join(remote_path, file_name)

            # Normalize path for SFTP consistency
            file_path = sftp.normalize(file_path)

            logger.debug(f"Evaluating File: {file_name} | Path: {file_path}")

            # Skip files based on size, time, and exclusion criteria
            if file_attr.st_size <= cutoff_size:
                logger.debug(f"Skipping {file_name} due to size: {file_attr.st_size}")
                continue
            if datetime.datetime.fromtimestamp(file_attr.st_mtime) > cutoff_time:
                logger.debug(f"Skipping {file_name} due to modification time: {file_attr.st_mtime}")
                continue
            if any(ext in file_name.lower() for ext in excluded_extensions):
                logger.debug(f"Skipping {file_name} due to excluded extension")
                continue
            if any(keyword in file_name.lower() for keyword in excluded_keywords):
                logger.debug(f"Skipping {file_name} due to excluded keyword")
                continue

            file_info = {
                "name": file_name,
                "size": file_attr.st_size,
                "modified_time": datetime.datetime.fromtimestamp(file_attr.st_mtime).isoformat(),
                "path": file_path,
                "fetched_at": datetime.datetime.now().isoformat(),
                "is_dir": stat.S_ISDIR(file_attr.st_mode)
            }

            logger.debug(f"Adding File: {file_info}")
            file_list.append(file_info)

            # Recursively process subdirectories
            if recursive and file_info["is_dir"]:
                logger.debug(f"Recursively scanning directory: {file_info['path']}")
                subdir_files = list_sftp_files(file_info["path"], sftp, cuttime, cutsize, recursive)
                file_list.extend(subdir_files)

    except Exception as e:
        logger.error(f"Error listing files in path {remote_path}: {e}")

    finally:
        if not recursive:
            if sftp:
                logger.debug("Closing SFTP connection for path: {remote_path}.")
                sftp.close()
            if transport:
                logger.debug("Closing transport connection for path: {remote_path}.")
                transport.close()

    return file_list

def download_files_from_sftp(file_list, sftp=None):
    """Download files from the SFTP server, skipping already existing and matching files."""

    completed_files = []

    while file_list:
        file = file_list.pop()
        # Convert remote path to local path using the appropriate OS separator
        local_path = os.path.join(TRANSFERS_INCOMING, file['path'].replace(SFTP_PATH, "").lstrip("/")).replace("/", os.sep)
        remote_path = file['path']

        try:
            # Handle directories
            if file['is_dir']:
                if not os.path.exists(local_path):
                    logger.debug(f"Directory does not exist. Creating directory: {local_path}")
                    os.makedirs(local_path)
                    logger.debug(f"Directory created: {local_path}")
                else:
                    logger.debug(f"Directory already exists: {local_path}")
                completed_files.append(file)

            # Handle files
            else:
                if os.path.exists(local_path):
                    local_size = os.path.getsize(local_path)
                    remote_size = file['size']
                    logger.debug(f"Local file exists: {local_path} (Local size: {local_size}, Remote size: {remote_size})")

                    # Compare sizes to decide whether to download
                    if local_size == remote_size:
                        logger.debug(f"Skipping download. Local and remote file sizes match: {local_path}")
                        completed_files.append(file)
                        continue
                    else:
                        logger.debug(f"File size mismatch. Overwriting file: {local_path}")
                else:
                    logger.debug(f"Local file does not exist. Preparing to download: {local_path}")

                # Download the file (overwrite if it already exists with a different size)
                sftp.get(remote_path, local_path)
                logger.debug(f"File downloaded: {remote_path} to {local_path}")

                completed_files.append(file)

        except Exception as e:
            logger.error(f"Error downloading file: {remote_path} to {local_path}: {e}")

        finally:
            logger.debug(f"Remaining files to process: {len(file_list)}")
            logger.debug(f"Total completed files: {len(completed_files)}")

    # Insert file metadata after processing all files
    if completed_files:
        insert_sftp_files_metadata(completed_files, DB_FILE)
        logger.debug(f"Inserted metadata for {len(completed_files)} files into the database.")
    else:
        logger.debug("No files were downloaded or processed for metadata insertion.")


############################
###### SQL Functions #######
############################
def initialize_database(db_file):
    """Creates the SQLite database if it does not exist.

    Args:
        db_file (str, optional): The path to the SQLite database file. Defaults to DB_FILE.

    Returns:
        True: Indicates that the database was successfully created.
        False: Indicates that the database could not be created.
    """
    logger.debug(f"Initializing database: {db_file}")
    db_dir = os.path.dirname(db_file)
    if not create_directory(db_dir):
        return False

    try:
        logger.debug(f"Creating database: {db_file}")
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sftp_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified_time DATETIME NOT NULL,
                path TEXT NOT NULL,
                fetched_at DATETIME NOT NULL,
                is_dir BOOLEAN NOT NULL
                        )''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tv_shows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sys_name TEXT NOT NULL,
                sys_path TEXT NOT NULL,
                tvdb_name TEXT,
                tvdb_aliases TEXT,
                tvdb_id INTEGER,
                tvdb_series_id TEXT,
                tvdb_year INTEGER,
                tvdb_overview TEXT,
                fetched_at DATETIME,
                regex_include TEXT,
                regex_exclude TEXT,
                episodes TEXT,
                status TEXT
                        )''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sftp_temp_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified_time DATETIME NOT NULL,
                path TEXT NOT NULL,
                fetched_at DATETIME NOT NULL,
                is_dir BOOLEAN NOT NULL
                        )''')

        conn.commit()
    except sqlite3.Error as error:
        logger.debug(f"Error creating database: {error}")
        return False
    finally:
        conn.close()

    try:
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute('''SELECT sql FROM sqlite_master WHERE name IN ('sftp_files','tv_shows');''')


        tables = cursor.fetchall()

        for table in tables:
            logger.debug(f"Table: {table[0]}")
    except sqlite3.Error as error:
        logger.debug(f"Error checking database tables: {error}")
        return False
    finally:
        conn.close()

    return True

def reset_sftp_table(db_file):
    """Recreate the SFTP files table from the database."""
    try:
        logger.debug(f"Recreate SFTP Table: {db_file}")
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute('''DROP TABLE IF EXISTS sftp_files''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sftp_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified_time DATETIME NOT NULL,
                path TEXT NOT NULL,
                fetched_at DATETIME NOT NULL,
                is_dir BOOLEAN NOT NULL
                        )''')
        conn.commit()
    except sqlite3.Error as error:
        logger.debug(f"Error dropping SFTP Temp Table: {error}")
        return False
    finally:
        conn.close()

    return True

def search_show_in_db(show_name, db_file):
    """Search the local routing database for a show.

    Args:
        show_name (str): The name of the show to search for.
        db_file (str, optional): The path to the local routing database file. Defaults to DB_FILE.

    Returns:
          matches (list): A list of matching show records from the database.
    """
    try:

        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT sys_name, tvdb_name, tvdb_aliases, sys_path, tvdb_id, tvdb_series_id, tvdb_year, episodes, status 
            FROM tv_shows
            WHERE sys_name = ? OR tvdb_name = ? OR tvdb_aliases LIKE ?
        """, (show_name, show_name, f"%{show_name}%"))

        matches = cursor.fetchall()
        conn.close()
    except sqlite3.Error as error:
        logger.debug(f"Error searching database for show: {error}")
        return []
    finally:
        conn.close()

    return matches

def insert_sftp_files_metadata(files_list, db_file):
    """Insert file metadata into the SFTP files table.

    Args:
        files_list (list): A list of dictionaries containing file details.
        db_file (str, optional): The path to the local routing database file. Defaults to DB_FILE.

    Returns:
        True: Indicates that the files were successfully inserted into the table.
        False: Indicates that the files could not be inserted into the table.
    """

    try:
        logger.debug(f"Inserting file data into table: {db_file}")
        conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO sftp_files (name, size, modified_time, path, fetched_at, is_dir)
            VALUES (:name, :size, :modified_time, :path, :fetched_at, :is_dir)
        """, files_list)
        logger.debug(f"Conn Commit: {conn.total_changes} rows changed.")
        conn.commit()
    except sqlite3.Error as error:
        logger.debug(f"Error inserting file data into table: {error}")
        return False
    finally:
        if conn:
            conn.close()

def insert_sftp_temp_files_metadata(file_list, db_file):
    """Insert new SFTP file metadata into the temporary SFTP files table."""
    db_dir = os.path.dirname(db_file)
    if not create_directory(db_dir):
        return False

    # Drop the SFTP temp table if it exists
    try:
        logger.debug(f"Dropping Existing SFTP Temp Table: {db_file}")
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute('''DROP TABLE IF EXISTS sftp_temp_files''')
        conn.commit()
    except sqlite3.Error as error:
        logger.debug(f"Error dropping existing SFTP Temp Table: {error}")
        return False
    finally:
        conn.close()

    # Create the fresh SFTP temp table
    try:
        logger.debug(f"Creating SFTP Temp Table: {db_file}")
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sftp_temp_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified_time DATETIME NOT NULL,
                path TEXT NOT NULL,
                fetched_at DATETIME NOT NULL,
                is_dir BOOLEAN NOT NULL
                        )''')
        conn.commit()
    except sqlite3.Error as error:
        logger.debug(f"Error creating SFTP Temp Table: {error}")
        return False
    finally:
        conn.close()

    # Insert the temp data into the fresh SFTP temp table
    try:
        logger.debug(f"Inserting SFTP Temp Table data into: {db_file}")
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO sftp_temp_files (name, size, modified_time, path, fetched_at, is_dir)
            VALUES (:name, :size, :modified_time, :path, :fetched_at, :is_dir)
        """, file_list)
        logger.debug(f"Conn Commit: {conn.total_changes} rows changed in SFTP Temp Table.")
        conn.commit()
    except sqlite3.Error as error:
        logger.debug(f"Error inserting file data into SFTP Temp Table: {error}")
        return False
    finally:
        if conn:
            conn.commit()
            conn.close()

def get_sftp_diffs(db_file):
    """Get the differences between the SFTP files table and the SFTP temp files table."""
    try:
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""SELECT name, size, modified_time, path, is_dir FROM sftp_temp_files EXCEPT SELECT name, size, modified_time, path, is_dir FROM sftp_files""")
        diffs = cursor.fetchall()
        conn.close()
    except sqlite3.Error as error:
        logger.debug(f"Error getting SFTP diffs: {error}")
        return []

    return diffs

def create_show_record(show, show_info, db_file):
    sys_path = os.path.join(ROUTING_ANIME_TV, show)
    if not os.path.exists(sys_path):
        logger.debug(f"Path does not exist: {sys_path}")
        os.makedirs(sys_path, exist_ok=True)
        logger.debug(f"Created directory: {sys_path}")

    if not "aliases" in show_info:
        show_info["aliases"] = []
    if not "year" in show_info:
        show_info["year"] = None
    if not "overviews" in show_info:
        show_info["overviews"] = {}
    if not "eng" in show_info["overviews"]:
        show_info["overviews"]["eng"] = None
    if not "objectID" in show_info:
        show_info["objectID"] = None
    if not "tvdb_id" in show_info:
        show_info["tvdb_id"] = None
    if not "tvdb_series_id" in show_info:
        show_info["tvdb_series_id"] = None
    if not "name" in show_info:
        show_info["name"] = None
    if not "status" in show_info:
        show_info["status"] = None
    if not "episodes" in show_info:
        show_info["episodes"] = None

    try:
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tv_shows (sys_name, sys_path, tvdb_name, tvdb_aliases, tvdb_id, tvdb_series_id, tvdb_year, tvdb_overview, fetched_at, regex_include, regex_exclude, episodes, status)
            VALUES (:sys_name, :sys_path, :tvdb_name, :tvdb_aliases, :tvdb_id, :tvdb_object_id, :tvdb_year, :tvdb_overview, :fetched_at, :regex_include, :regex_exclude, :episodes, :status)
        ''', {
            "sys_name": show,
            "sys_path": sys_path,
            "tvdb_name": show_info["name"],
            "tvdb_aliases": json.dumps(show_info["aliases"]),
            "tvdb_id": show_info["tvdb_id"],
            "tvdb_object_id": show_info["objectID"],
            "tvdb_year": show_info["year"],
            "tvdb_overview": show_info["overviews"]["eng"],
            "fetched_at": datetime.datetime.now(),
            "regex_include": "",
            "regex_exclude": "",
            "episodes": "",
            "status": ""
        })
        logger.debug(f"Conn Commit: {conn.total_changes} rows changed.")
        conn.commit()
    except sqlite3.Error as error:
        logger.debug(f"Error inserting show record into table: {error}")
        return False
    finally:
        if conn:
            conn.close()

def update_show_status_and_episodes(tvdb_id, ser, eps, db_file):
    status = ser["status"]['name']
    episodes = json.dumps(eps)

    try:
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE tv_shows
            SET status = :status,
                episodes = :episodes
            WHERE tvdb_id = :tvdb_id
        ''', {
            "tvdb_id": tvdb_id,
            "status": status,
            "episodes": episodes
        })
        logger.debug(f"Conn Commit: {conn.total_changes} rows changed.")
        conn.commit()
    except sqlite3.Error as error:
        logger.debug(f"Error inserting show episodes and status into table: {error}")
        return False
    finally:
        if conn:
            conn.close()


############################
###### TVDB Functions ######
############################
def fetch_show_info(show_name):
    """Fetch show information from TVDB.

    Args:
        show_name (str): The name of the show to search for.

    Returns:
        search_results (dict): A dictionary containing the search results no exact matches found and no filtering applied.
        filtered_results (dict): A dictionary containing the filtered search results if no exact match found but filtered results found.
        exact_name (dict): A dictionary containing the exact name match if found.
        exact_trans (dict): A dictionary containing the exact translation match if found.
        None: If no results are found.

    """
    search_results = tvdb.search(show_name)
    if search_results:

        if len(search_results) == 1:
            logger.debug(f"Precise match found: {show_name}")
            return search_results[0]

        elif len(search_results) > 1:
            # Check if the search results contain the exact show name or a translation of the show name
            exact_name = [
                series for series in search_results
                if str.lower(series.get('name', '')) == str.lower(show_name)  # Ensure 'name' exists and matches
                ]

            exact_trans = [
                series for series in search_results
                if isinstance(series.get('translations'), dict)  # Ensure translations is a dict
                and str.lower(series['translations'].get('eng', '')) == str.lower(show_name)
                ]

            if exact_name:
                logger.debug(f"Exact name found: {exact_name[0]}")
                return exact_name[0]
            elif exact_trans:
                logger.debug(f"Exact translation found: {exact_trans[0]}")
                return exact_trans[0]
            else:
                logger.debug(f"Multiple results found for: {show_name}")
                filtered_results = [
                series for series in search_results
                if series.get('country') == 'jpn'
                and series.get('primary_type') == 'series'
                and series.get('aliases') is not None
                and any(str.lower(alias) == str.lower(show_name) for alias in series['aliases'])]

                if filtered_results:
                    return filtered_results[0]
                else:
                    return search_results[0]
        else:
            logger.debug(f"Search Results not working for: {show_name}")
            return None
    else:
        logger.debug(f"No results found for: {show_name}")
        return None

def fetch_episode_info(tvdb_id):
    try:
        data = tvdb.get_series_episodes(tvdb_id)
        series = data['series']
        episodes = data['episodes']
        return series, episodes
    except Exception as e:
        logger.debug(f"Error fetching episode info: {e}")
        return None, None

def determine_season_from_tvdb(show_name, episode):
    """Determine the season and episode number from the show database."""
    season = None

    try:
        episode = int(episode)
    except ValueError:
        return None, None

    match = search_show_in_db(show_name, DB_FILE)

    if not match:
        logger.debug(f"Show not found in database: {show_name}")
        return None, None
    else:
        for m in match:
            sys_name, tvdb_name, tvdb_aliases, sys_path, tvdb_id, tvdb_series_id, tvdb_year, episodes, status = m

            eps = json.loads(episodes)
            for idx, e in enumerate(eps):
                if episode == eps[idx]['absoluteNumber']:
                    season = str(eps[idx]['seasonNumber']).zfill(2)
                    new_episode = str(eps[idx]['number']).zfill(2)
                    break
                else:
                    new_episode = episode

    return season, new_episode

def build_metadata(file_list):
    """Build metadata for the incoming files."""

    # Identification regexes
    # bracket_title_abseps_regex = re.compile(r"\[.*?\]\s*(?!.*\bS\d+\b)(.*?)(?:\s*\((\d{4})\))?\s*-\s*(\d+)")
        # [Info] (Title of Show) - (Episode#) ...
        # [Info] (Title of Show) - (Year) - (Episode#) ...
    # bracket_title_s_abseps_regex = re.compile(r"\[.*?\]\s*(.*?)\sS(\d+)\s*-\s*(\d+)")
        # [Info] (Title of Show) S(Season#) - (Episode#) ...
    # title_season_eps_regex = re.compile(r"^(.*?)(?:[.\-](\d{4}))?[.\-]S(\d{2})E(\d{2})")
        # (Title of Show) .|- (Year) .|- S(Season#)E(Episode#) ...

    metadata = []

    pattern = re.compile(
        r'(?:\[.*?\]\s*(?!.*\bS\d+\b)(.*?)(?:\s*\((\d{4})\))?\s*-\s*(\d+))|'
        r'(?:\[.*?\]\s*(.*?)\sS(\d+)\s*-\s*(\d+))|'
        r'(?:^(.*?)(?:[.\-](\d{4}))?[.\-]S(\d{2})E(\d{2}))'
    )

    for file in file_list:
        show_name, year, season, episode, filepath, filename, sys_name, sys_path, tvdb_id = None, None, None, None, None, None, None, None, None

        # Extract the filename from the full path
        filepath, filename = os.path.split(file)
        logger.debug(f"Filepath: {filepath}, Filename: {filename}")

        match = pattern.match(filename)
        if match:
            groups = match.groups()

            # Determine which regex matched based on non-None groups
            if groups[0]:  # First regex (non-season title) ... bracket_title_abseps_regex
                show_name, year, episode = groups[0], groups[1] or "N/A", groups[2]
                season = "N/A"
            elif groups[3]:  # Second regex (season included) ... bracket_title_s_abseps_regex
                show_name, season, episode = groups[3], groups[4], groups[5]
                year = "N/A"
            elif groups[6]:  # Third regex (SxxExx format) ... title_season_eps_regex
                show_name, year, season, episode = groups[6], groups[7] or "N/A", groups[8], groups[9]

        logger.debug(f"Processing ... Title: {show_name}, Year: {year}, Season: {season}, Episode: {episode}")

        # Safeguard against None values
        if not show_name:
            logger.error(f"Unable to extract show name from filename: {filename}")
            continue

        # Commenting out for the moment ... some show names have legitimate periods in the filename
        # TODO: Pass the clean and dirty forms of the show name to resolve.
        # Clean up the show name
        #show_name = show_name.replace(".", " ").strip()

        # Handle missing season and try to resolve from TVDB
        if not season or season == "N/A":
            season, new_episode = determine_season_from_tvdb(show_name, episode)
            if not new_episode:
                logger.debug(f"No episode found for {show_name} - {season} - {episode}")
                continue
            else:
                episode = new_episode
                logger.debug(f"New episode found for {show_name} - {season} - {episode}")

        # Ensure episode and season strings are zfill'd
        episode = str(episode).zfill(2)
        season = str(season).zfill(2)

        logger.debug(f"Searching Database For Show: {show_name}")
        db_match = search_show_in_db(show_name, DB_FILE)
        if db_match:
            for m in db_match:
                sys_name, tvdb_name, tvdb_aliases, sys_path, tvdb_id, tvdb_series_id, tvdb_year, episodes, status = m

            md = (show_name, year, season, episode, filename, filepath, sys_name, sys_path, tvdb_id)
            logger.debug(f"Appending Metadata: {md}")
            metadata.append(md)
        else:
            logger.debug(f"Show not found in database: {show_name}")
            continue

    return metadata


############################
### Filesystem Functions ###
############################
def create_directory(dir_path):
    """Create a directory if it does not exist."""
    if not os.path.exists(dir_path):
        try:
            logger.debug(f"Creating directory: {dir_path}")
            os.makedirs(dir_path)
            logger.debug(f"Directory created: {dir_path}")
        except OSError as e:
            logger.debug(f"Error creating directory: {e}")
            return False
    return True

def read_file_to_list(file_path):
    """Read a file and return a list of lines.

    Args:
        file_path (str): The path to the file to read.

    Returns:
        (list): A list of lines from the file.
    """
    try:
        with open(file_path, "r") as file:
            return [line.strip() for line in file]
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def list_files_incoming(path):
    """List files in the incoming directory.

    Args:
        path (str, optional): The path to the incoming directory. Defaults to TRANSFERS_INCOMING.

    Returns:
        incoming_files (set): A set of file paths in the incoming directory.
    """
    incoming_files = set()
    for root, dirs, files in os.walk(path):
        for file in files:
            incoming_files.add(os.path.join(root,file))
    return incoming_files

def check_for_db(db_file):
    """Check if the database file exists and is a file.
    Args:
        db_file (str, optional): The path to the database file. Defaults to DB_FILE.

    Returns:
        True: Indicates that the database file exists and is a file.
        False: Indicates that the database file does not exist or is not a file.
    """
    if os.path.exists(db_file) & os.path.isfile(db_file):
        logger.debug(f"Database file found: {db_file}")
        return True
    else:
        logger.debug(f"Database file not found: {db_file}")
        if initialize_database(db_file):
            logger.debug(f"Database file created: {db_file}")
            return True
        else:
            logger.debug(f"Error initializing database: {db_file}")
            return False

def file_router(metadata):
    """Route the incoming files to the appropriate directories."""
    for data in metadata:
        show_name, year, season, episode, filename, filepath, sys_name, sys_path, tvdb_id = data

        # Check if the show is in the database
        if sys_name:
            # If the show is in the database, move the file to the appropriate directory
            if season:
                new_path = os.path.join(sys_path, f"Season {season}")
            else:
                new_path = sys_path

            # Create the new path if it doesn't exist
            if not os.path.exists(new_path):
                logger.debug(f"Creating directory: {new_path}")
                os.makedirs(new_path)

            # Move the file
            logger.debug(f"Moving {filename} to {new_path}")
            shutil.move(os.path.join(filepath, filename), os.path.join(new_path, filename))
            logger.debug(f"Moved {filename} to {new_path}")

        # If the show is not in the database, search TheTVDB for the show
        else:
            logger.debug(f"Show not found in metadata: {show_name}")


############################
####### Main Program #######
############################
def main():
    """Main function to run the script."""

    # 1. Check the database exists and initialize it if not
    if not check_for_db(DB_FILE):
        logger.error(f"Database file does not exist: {DB_FILE}")
        return

    # Create Show
    if args.create_show:
        show_name = args.create_show
        show_already_exists = search_show_in_db(show_name, DB_FILE)
        if not show_already_exists:
            logger.debug(f"Fetching show info from TVDB: {show_name}")
            show_info = fetch_show_info(show_name)
            if show_info:
                create_show_record(show_name, show_info, DB_FILE)
                ser, eps = fetch_episode_info(show_info["tvdb_id"])
                update_show_status_and_episodes(show_info["tvdb_id"], ser, eps, DB_FILE)
                logger.debug(f"Show created: {show_name}")
            else:
                logger.debug(f"Show not found: {show_name}")
        else:
            logger.debug(f"Show already exists: {show_name}")

    # 2. List/Download files on the SFTP server
    if args.full_sftp_table_refresh: # Performing a full database refresh of the SFTP server files
        _sftp, _transport = _connect_sftp(SFTP_HOST, SFTP_PORT, SFTP_USERNAME, SSH_KEY_PATH)
        try:
            logger.debug("Refreshing SFTP table with all files.")
            file_list = list_sftp_files(sftp=_sftp, remote_path=SFTP_PATH, recursive=True)
            logger.debug(f"Total files found: {len(file_list)}")

            # Recreate existing sftp files table and populate
            reset_sftp_table(DB_FILE)
            check_for_db(DB_FILE)
            insert_sftp_files_metadata(file_list, DB_FILE) # Insert into db
        except Exception as e:
            logger.error(f"Error refreshing SFTP table: {e}")
        finally:
            if _sftp:
                _sftp.close()
            if _transport:
                _transport.close()
    # Updating the existing database with new files from the SFTP server
    elif args.download_files:
        # Check new sftp dir vs database and create file_list
        _sftp, _transport = _connect_sftp(SFTP_HOST, SFTP_PORT, SFTP_USERNAME, SSH_KEY_PATH)
        try:
            new_file_list = [] # Create empty list that will be eventually added to db
            logger.debug("Fetching new SFTP file information.")
            sftp_file_list = list_sftp_files(sftp=_sftp, remote_path=SFTP_PATH, recursive=False) # get SFTP path list of files, no recursion
            logger.debug(f"Total top level files found on SFTP server: {len(sftp_file_list)}")
            insert_sftp_temp_files_metadata(sftp_file_list, DB_FILE) # Insert the sftp path list into the temp table
            diff_files = get_sftp_diffs(DB_FILE) # Diff the standard table and the temp table
            logger.debug(f"New top level files found on SFTP server: {len(diff_files)}")
            # a. Recursive ftp on the diff files
            for file in diff_files:
                if file['is_dir'] == 1: # if the file in the diff list is a directory, recursively search it
                    logger.debug(f"Recursive sftp on directory: {file['path']}")
                    f = {k: file[k] for k in file.keys()} # We want the dir in the db, too so fix the sqlite.Row to dict
                    f['fetched_at'] = datetime.datetime.now().isoformat() # Add the fetched_at field
                    new_file_list.append(f) # Append the directory record to the new_file_list so it can be added to the db
                    dir_file_list = list_sftp_files(sftp=_sftp, remote_path=file['path'], recursive=True) # search the dir recursively
                    logger.info(f"Total files in {file['path']} found: {len(dir_file_list)}")
                    new_file_list.extend(dir_file_list) # extend the new file list with the recursive files
                else:
                    logger.debug(f"Non-recursive sftp on file: {file['path']}")
                    f = {k: file[k] for k in file.keys()}
                    f['fetched_at'] = datetime.datetime.now().isoformat()
                    new_file_list.append(f) # just a standard file, add it to the new_file_list
            # b. Insert into db
            logger.debug(f"Total new files found: {len(new_file_list)}")
            logger.debug(f"New files: {[f['name'] for f in new_file_list]}")
            # Download new files & insert into db
            download_files_from_sftp(new_file_list,_sftp)

        except Exception as e:
            logger.error(f"Error fetching new SFTP file information: {e}")
        finally:
            if _sftp:
                _sftp.close()
            if _transport:
                _transport.close()
    else:
        pass

    # 3. Route
    if args.route_files:
        # List files in the incoming directory
        incoming_files = list_files_incoming(TRANSFERS_INCOMING)
        logger.debug(f"Total incoming files found: {len(incoming_files)}")
        # Enrich the files with TVDB metadata
        enriched_file_metadata = build_metadata(incoming_files)
        logger.debug(f"Total enriched files found: {len(enriched_file_metadata)}")
        if enriched_file_metadata:
            logger.debug(f"Total enriched files found: {len(enriched_file_metadata)}")
            file_router(enriched_file_metadata)
        else:
            logger.error("No files found to route.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronize SFTP files to NAS.")
    parser.add_argument("-c", "--config", dest="config_ini", default="./config/sync2nas_config.ini", type=str, help="Specify a configuration file.")
    parser.add_argument("-r", "--route-files", dest="route_files", action='store_true', help="Route files to the appropriate directories from Incoming directory to NAS.")
    parser.add_argument("-d", "--download-files", dest="download_files", action='store_true', help="Download files from the SFTP server to the Incoming directory.")
    parser.add_argument("--full-sftp-table-refresh", dest="full_sftp_table_refresh", action='store_true', help="Refresh the SFTP table with all files.")
    parser.add_argument("--search-show", type=str, default=None, help="Search for a show on TVDB.")
    parser.add_argument("--update-show", type=int, nargs='+', default=None, help="Update a show from TVDB. Local DB ID first, then TVDB ID.")
    parser.add_argument("--update-episodes", type=int, nargs='+', default=None, help="Update the episodes a show from TVDB using the series tvdb_id.")
    parser.add_argument("--update-all-episodes", action="store_true",  help="Update all episodes for show in the database.")
    parser.add_argument("--create-show", type=str, dest="create_show", default=None, help="Create a new show record in the database and filesystem.")
    parser.add_argument("-v", "--verbose", dest="verbose", default=True, action='store_false', help="Enable verbose output.")

    args: Namespace = parser.parse_args()

    ############################
    ## ConfigParser Variables ##
    ############################
    config = configparser.ConfigParser()
    config.read(args.config_ini)

    SFTP_HOST = config["SFTP"]["host"]
    SFTP_PORT = int(config["SFTP"]["port"])
    SFTP_USERNAME = config["SFTP"]["username"]
    SSH_KEY_PATH = config["SFTP"]["ssh_key_path"]
    SFTP_PATH = config["SFTP"]["path"]
    DB_FILE = config["SQLite"]["db_file"]
    TVDB_API = config["TVDB"]["api_key"]
    ROUTING_TV = config["Routing"]["tv_path"]
    ROUTING_ANIME_TV = config["Routing"]["anime_tv_path"]
    TRANSFERS_INCOMING = config["Transfers"]["incoming"]

    # Create a new instance of the TVDB class
    tvdb = tvdb.TVDB(TVDB_API)

    # Setup logging based on verbosity
    setup_logging(args.verbose)

    main()