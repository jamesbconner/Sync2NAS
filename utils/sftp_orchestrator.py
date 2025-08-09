"""
SFTP orchestrator utilities for processing SFTP diffs, downloading files, and bootstrapping file tables.
"""
import os
import logging
import datetime
from typing import List, Dict, Optional
from services.sftp_service import SFTPService
from services.db_implementations.db_interface import DatabaseInterface
from utils.file_filters import is_valid_media_file, is_valid_directory
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from models.downloaded_file import DownloadedFile
from services.hashing_service import HashingService
from utils.filename_parser import parse_filename

logger = logging.getLogger(__name__)

def process_sftp_diffs(
    sftp_service: SFTPService,
    db_service: DatabaseInterface,
    diffs: List[Dict],
    remote_base: str,
    local_base: str,
    dry_run: bool = False,
    llm_service=None,
    max_workers: int = 4,
    hashing_service: Optional[HashingService] = None,
    parse_filenames: bool = True,
    use_llm: bool = True,
    llm_confidence_threshold: float = 0.7,
) -> None:
    """
    Process a list of SFTP diffs: download new files or directories and record them.
    Now supports concurrent file downloads using a thread pool.
    
        Args:
        sftp_service (SFTPService): SFTP service instance.
        db_service (DatabaseInterface): Database interface for file tracking.
        diffs (List[Dict]): List of file/dir diffs to process.
        remote_base (str): Root remote path.
        local_base (str): Root local path.
        dry_run (bool): If True, perform no download or DB writes.
        llm_service: Optional LLM service for directory name suggestions.
        max_workers (int): Number of concurrent download threads for files.
    Returns:
        None
    """
    # Extract SFTP connection parameters from the provided sftp_service
    sftp_params = {
        "host": sftp_service.host,
        "port": sftp_service.port,
        "username": sftp_service.username,
        "ssh_key_path": sftp_service.ssh_key_path,
        "llm_service": sftp_service.llm_service,
    }
    # Determine effective LLM service
    active_llm_service = llm_service or getattr(sftp_service, "llm_service", None)
    logger.info(
        "SFTP processing config: parse_filenames=%s, use_llm=%s, llm_confidence_threshold=%.2f, max_workers=%d",
        parse_filenames,
        use_llm,
        llm_confidence_threshold,
        max_workers,
    )
    if not parse_filenames:
        logger.info("Filename parsing is disabled; show/season/episode will not be populated.")
    elif not use_llm or active_llm_service is None:
        logger.info("LLM parsing disabled or unavailable; regex fallback will be used for filename parsing.")

    def download_file_task(remote_path, local_path):
        sftp = SFTPService(**sftp_params)
        with sftp:
            start_ts = datetime.datetime.now()
            sftp.download_file(remote_path, local_path)
            duration = (datetime.datetime.now() - start_ts).total_seconds()
            logger.info(f"Downloaded {remote_path} -> {local_path} in {duration:.2f}s")

    # Separate files and directories
    file_entries = []
    dir_entries = []
    for entry in diffs:
        name = entry["name"]
        remote_path = entry.get("remote_path") or entry.get("path")
        relative_path = os.path.relpath(remote_path, remote_base)
        local_path = os.path.join(local_base, relative_path)
        entry['fetched_at'] = datetime.datetime.now()

        if entry["is_dir"]:
            if not is_valid_directory(name):
                logger.info(f"Skipping directory due to filter: {name}")
                continue
            dir_entries.append((entry, remote_path, local_path))
        else:
            if not is_valid_media_file(name):
                logger.info(f"Skipping file due to filter: {name}")
                continue
            file_entries.append((entry, remote_path, local_path))

    # Download directories sequentially (can be parallelized in future)
    for entry, remote_path, local_path in dir_entries:
        if dry_run:
            logger.info(f"DRY RUN - Would download DIR: {remote_path} -> {local_path}")
            continue
        try:
            logger.info(f"Starting download of DIR: {remote_path} -> {local_path}")
            sftp_service.download_dir(remote_path, local_path, max_workers=max_workers)
            db_service.add_downloaded_file({**entry, "path": entry.get("remote_path") or entry.get("path")})
            # Upsert record via DB service
            try:
                file_model = DownloadedFile.from_sftp_entry(
                    {**entry, "path": entry.get("remote_path") or entry.get("path"), "local_path": local_path},
                    base_path=local_base,
                )
                db_service.upsert_downloaded_file(file_model)
            except Exception as repo_exc:
                logger.warning(f"DownloadedFile upsert failed for DIR {remote_path}: {repo_exc}")
            logger.info(f"Downloaded DIR: {remote_path} -> {local_path}")
        except Exception as e:
            logger.exception(f"Failed to download DIR {remote_path}: {e}")

    # Download files concurrently
    if file_entries:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_entry = {}
            for entry, remote_path, local_path in file_entries:
                if dry_run:
                    logger.info(f"DRY RUN - Would download FILE: {remote_path} -> {local_path}")
                    continue
                future = executor.submit(download_file_task, remote_path, local_path)
                future_to_entry[future] = (entry, remote_path, local_path)
            for future in as_completed(future_to_entry):
                entry, remote_path, local_path = future_to_entry[future]
                try:
                    future.result()
                    db_service.add_downloaded_file({**entry, "path": entry.get("remote_path") or entry.get("path")})
                    # Upsert record via DB service
                    try:
                        file_model = DownloadedFile.from_sftp_entry(
                            {**entry, "path": entry.get("remote_path") or entry.get("path"), "local_path": local_path},
                            base_path=local_base,
                        )
                        # Parse filename to populate show/season/episode if enabled
                        if parse_filenames and not entry.get("is_dir", False):
                            try:
                                metadata = parse_filename(
                                    file_model.name,
                                    llm_service=active_llm_service if use_llm else None,
                                    llm_confidence_threshold=llm_confidence_threshold,
                                )
                                file_model.show_name = metadata.get("show_name")
                                file_model.season = metadata.get("season")
                                file_model.episode = metadata.get("episode")
                                file_model.confidence = metadata.get("confidence")
                                file_model.reasoning = metadata.get("reasoning")
                                method = (
                                    "LLM"
                                    if (
                                        use_llm
                                        and active_llm_service is not None
                                        and file_model.confidence is not None
                                        and file_model.confidence >= llm_confidence_threshold
                                    )
                                    else "regex"
                                )
                                def _fmt_num(value):
                                    try:
                                        return f"{int(value):02d}"
                                    except Exception:
                                        return "??"
                                s_display = _fmt_num(file_model.season)
                                e_display = _fmt_num(file_model.episode)
                                logger.info(
                                    "Parsed '%s' via %s: show='%s' S%s E%s (confidence=%.2f)",
                                    file_model.name,
                                    method,
                                    file_model.show_name,
                                    s_display,
                                    e_display,
                                    (file_model.confidence if file_model.confidence is not None else 0.0),
                                )
                                logger.debug("Parsing details for '%s': %s", file_model.name, metadata)
                            except Exception as p_exc:
                                logger.warning(f"Filename parsing failed for {file_model.name}: {p_exc}")
                        # Compute CRC32 if hashing_service provided
                        if hashing_service is not None and not entry.get("is_dir", False):
                            try:
                                hash_start = datetime.datetime.now()
                                crc = hashing_service.calculate_crc32(local_path)
                                hash_end = datetime.datetime.now()
                                file_model.file_hash = crc
                                file_model.file_hash_algo = "CRC32"
                                file_model.hash_calculated_at = hash_end
                                hash_secs = (hash_end - hash_start).total_seconds()
                                logger.info(f"CRC32 computed for {local_path} in {hash_secs:.2f}s")
                            except Exception as h_exc:
                                logger.warning(f"CRC32 compute failed for {local_path}: {h_exc}")
                        upsert_start = datetime.datetime.now()
                        db_service.upsert_downloaded_file(file_model)
                        upsert_secs = (datetime.datetime.now() - upsert_start).total_seconds()
                        logger.info(f"Upserted DownloadedFile for {local_path} in {upsert_secs:.2f}s")
                    except Exception as repo_exc:
                        logger.warning(f"DownloadedFile upsert failed for FILE {remote_path}: {repo_exc}")
                    logger.info(f"Downloaded FILE: {remote_path} -> {local_path}")
                except Exception as e:
                    logger.exception(f"Failed to download FILE {remote_path}: {e}")

def download_from_remote(
    sftp: SFTPService,
    db: DatabaseInterface,
    remote_paths: List[str],
    incoming_path: str,
    dry_run: bool = False,
    max_workers: int = 4,
    hashing_service: Optional[HashingService] = None,
    parse_filenames: bool = True,
    use_llm: bool = True,
    llm_confidence_threshold: float = 0.7,
) -> None:
    """
    Orchestrates remote file download:
    - List and store files in sftp_temp_files
    - Diff against downloaded_files
    - Download missing files
    - Record downloads

    Args:
        sftp (SFTPService): SFTP service instance.
        db (DatabaseInterface): Database interface.
        remote_paths (List[str]): List of remote paths to process.
        incoming_path (str): Local incoming directory.
        dry_run (bool): If True, simulate actions without downloading or DB writes.
        max_workers (int): Number of concurrent download threads for files.

    Returns:
        None
    """
    for remote_path in remote_paths:
        logger.info(f"Processing remote path: {remote_path}")

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
            max_workers=max_workers,
            hashing_service=hashing_service,
            parse_filenames=parse_filenames,
            use_llm=use_llm,
            llm_confidence_threshold=llm_confidence_threshold,
        )

def list_remote_files(sftp_service: SFTPService, remote_path: str) -> List[Dict]:
    """
    List files in the given SFTP path with filtering rules applied.

    Filtering excludes:
    - Files with certain extensions
    - Files/folders with keywords like 'sample' or 'screens'
    - Files modified less than 1 minute ago

    Args:
        sftp_service (SFTPService): SFTP service instance.
        remote_path (str): Remote directory to scan.

    Returns:
        List[Dict]: List of filtered file metadata dictionaries.
    """

    raw_files = sftp_service.list_remote_dir(remote_path)

    filtered = []
    now = datetime.datetime.now()

    for entry in raw_files:
        name = entry.get("name", "")
        is_dir = entry.get("is_dir", False)

        # Use utils/file_filters.py for filtering
        if is_dir:
            if not is_valid_directory(name):
                logger.debug(f"Excluded directory by keyword: {entry['name']}")
                continue
        else:
            if not is_valid_media_file(name):
                logger.debug(f"Excluded file by extension/keyword: {entry['name']}")
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

def bootstrap_downloaded_files(sftp: SFTPService, db: DatabaseInterface, remote_paths: List[str]) -> None:
    """
    Populate the `downloaded_files` table from the current remote SFTP listing.

    This clears and repopulates the `sftp_temp_files` table first, then copies it into `downloaded_files`.

    Args:
        sftp (SFTPService): SFTP service instance.
        db (DatabaseInterface): Database interface.
        remote_paths (List[str]): List of remote paths to process.

    Returns:
        None
    """
    for remote_path in remote_paths:
        files = list_remote_files(sftp, remote_path)
        db.clear_sftp_temp_files()
        db.clear_downloaded_files()
        db.insert_sftp_temp_files(files)
        db.copy_sftp_temp_to_downloaded()
        logger.info(f"Bootstrapped {len(files)} entries into downloaded_files from remote path.")