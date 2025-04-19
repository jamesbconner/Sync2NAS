import os
import logging
import datetime
from typing import List, Dict
from services.sftp_service import SFTPService
from services.db_service import DBService

logger = logging.getLogger(__name__)

def process_sftp_diffs(
    sftp_service,
    db_service,
    diffs: List[Dict],
    remote_base: str,
    local_base: str,
    dry_run: bool = False):
    """
    Process a list of SFTP diffs: download new files or directories and record them.

    Args:
        sftp_service: SFTPService instance (must have download_file and download_dir).
        db_service: DBService instance.
        diffs: List of dicts from get_sftp_diffs.
        remote_base: Root remote path.
        local_base: Root local path.
        dry_run: If True, perform no download or DB writes.
    """
    for entry in diffs:
        name = entry["name"]
        remote_path = entry["path"]
        relative_path = os.path.relpath(remote_path, remote_base)
        local_path = os.path.join(local_base, relative_path)
        entry['fetched_at'] = datetime.datetime.now()

        if entry["is_dir"]:
            entry_type = "DIR"
        else:
            entry_type = "FILE"

        if dry_run:
            logger.info(f"DRY RUN - Would download {entry_type}: {remote_path} -> {local_path}")
            continue

        try:
            if entry["is_dir"]:
                sftp_service.download_dir(remote_path, local_path)
            else:
                sftp_service.download_file(remote_path, local_path)
            
            # ToDo: This only works for the top level objects in the sftp path. Need to update to work for nested directories.
            db_service.add_downloaded_file(entry)
            logger.info(f"Downloaded {entry_type}: {remote_path} -> {local_path}")
        except Exception as e:
            logger.error(f"Failed to download {entry_type} {remote_path}: {e}")

def download_from_remote(sftp, db, remote_path: str, incoming_path: str, dry_run: bool = False):
    """
    Orchestrates remote file download:
    - List and store files in sftp_temp_files
    - Diff against downloaded_files
    - Download missing files
    - Record downloads
    """

    # Step 1: List files and populate sftp_temp_files
    remote_files = list_remote_files(sftp, remote_path)
    db.clear_sftp_temp_files()
    db.insert_sftp_temp_files(remote_files)

    # Step 2: Diff against already downloaded files
    diffs = db.get_sftp_diffs()
    logger.info(f"{len(diffs)} new file(s)/dir(s) to download.")

    # Step 3: Delegate to processor
    process_sftp_diffs(
        sftp_service=sftp,
        db_service=db,
        diffs=diffs,
        remote_base=remote_path,
        local_base=incoming_path,
        dry_run=dry_run,
    )

def list_remote_files(sftp_service, remote_path: str) -> List[Dict]:
    """
    List files in the given SFTP path with filtering rules applied.

    Filtering excludes:
    - Files with certain extensions
    - Files/folders with keywords like 'sample' or 'screens'
    - Files modified less than 1 minute ago

    Args:
        sftp_service: An instance of SFTPService
        remote_path: Remote directory to scan

    Returns:
        List of filtered file metadata dictionaries
    """

    EXCLUDED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".nfo", ".sfv"}
    EXCLUDED_KEYWORDS = {"screens", "sample"}

    raw_files = sftp_service.list_remote_dir(remote_path)

    filtered = []
    now = datetime.datetime.now()

    for entry in raw_files:
        name = entry.get("name", "").lower()
        is_dir = entry.get("is_dir", False)

        # Exclude by keyword in name
        if any(keyword in name for keyword in EXCLUDED_KEYWORDS):
            logger.debug(f"Excluded by keyword: {entry['name']}")
            continue

        # Exclude by extension
        if not is_dir and any(name.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
            logger.debug(f"Excluded by extension: {entry['name']}")
            continue

        # Exclude files modified in the last minute
        modified_time = entry.get("modified_time")
        if not is_dir and modified_time:
            try:
                mod_time_dt = (
                    modified_time
                    if isinstance(modified_time, datetime.datetime)
                    else datetime.datetime.strptime(modified_time, "%Y-%m-%d %H:%M:%S")
                )
                if (now - mod_time_dt) < datetime.timedelta(minutes=1):
                    logger.debug(f"Excluded by mtime < 1min: {entry['name']}")
                    continue
            except Exception as e:
                logger.warning(f"Could not parse modified_time for {entry['name']}: {e}")

        filtered.append(entry)

    return filtered

def bootstrap_downloaded_files(sftp: SFTPService, db: DBService, remote_path: str):
    """
    Populate the `downloaded_files` table from the current remote SFTP listing.

    This clears and repopulates the `sftp_temp_files` table first, then copies it into `downloaded_files`.
    """
    files = list_remote_files(sftp, remote_path)
    db.clear_sftp_temp_files()
    db.clear_downloaded_files()
    db.insert_sftp_temp_files(files)
    db.copy_sftp_temp_to_downloaded()
    logger.info(f"Bootstrapped {len(files)} entries into downloaded_files from remote path.")