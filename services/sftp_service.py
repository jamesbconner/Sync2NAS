import functools
import socket
import time
import paramiko
import logging
import os
import stat
from pathlib import Path
from datetime import datetime
from datetime import timedelta
from utils.file_filters import is_valid_media_file
from utils.file_filters import is_valid_directory
from utils.filename_parser import parse_filename
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

def retry_sftp_operation(func):
    """Decorator factory to retry SFTP operations in case of connection errors."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        max_retries=3
        delay=5
        attempts = 0
        operation_name = getattr(func, "__name__", str(func))
        logger.debug(f"Starting SFTP operation: {operation_name} with up to {max_retries} retries.")

        while attempts < max_retries:
            try:
                return func(self, *args, **kwargs)
            except (paramiko.SSHException, socket.error) as e:
                attempts += 1
                logger.warning(f"SFTP operation '{operation_name}' failed: {e}. Retry {attempts}/{max_retries}.")
                if attempts >= max_retries:
                    logger.error(f"SFTP operation '{operation_name}' failed after {max_retries} retries.")
                    raise
                time.sleep(delay)
                self.reconnect()
    return wrapper
        

class SFTPService:
    """
    Service for managing SFTP connections and file operations, including listing, downloading, and filtering remote files.

    Methods:
        connect(): Establish a new SFTP connection.
        disconnect(): Close the SFTP connection.
        reconnect(): Reconnect to the SFTP server.
        list_remote_dir(remote_path): List contents of a remote directory.
        list_remote_files(remote_path): List files in a remote directory.
        list_remote_files_recursive(remote_path): Recursively list files in a remote directory.
        download_dir(remote_path, local_path, filename_map): Download a directory from remote.
        download_file(remote_path, local_path, max_path_length): Download a file from remote.
    """
    def __init__(self, host, port, username, ssh_key_path, llm_service=None):
        self.host = host
        self.port = port
        self.username = username
        self.ssh_key_path = ssh_key_path
        self.client = None
        self.transport = None
        self.llm_service = llm_service
        
        if llm_service is None:
            logger.warning("No LLM service provided.")
        else:
            logger.info(f"LLM service: {llm_service}")

    def __enter__(self):
        try:
            self.connect()
            return self
        except Exception as e:
            logger.exception(f"Error establishing SFTP connection: {e}")
            self.__exit__(None, None, None)
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.client:
                self.client.close()
                self.client = None
        except Exception as e:
            logger.exception(f"Error closing SFTP client: {e}")
        
        try:
            if self.transport:
                self.transport.close()
                self.transport = None
        except Exception as e:
            logger.exception(f"Error closing transport: {e}")

    def connect(self):
        """Establish a new SFTP connection."""
        try:
            key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
            self.transport = paramiko.Transport((self.host, self.port))
            self.transport.connect(username=self.username, pkey=key)
            self.client = paramiko.SFTPClient.from_transport(self.transport)
            logger.debug("SFTP connection established successfully.")
            return self
        except Exception as e:
            logger.exception(f"Failed to establish SFTP connection to {self.host}:{self.port} with error: {e}")
            self.__exit__(None, None, None)
            raise RuntimeError(f"Failed to connect to SFTP server: {e}")

    def disconnect(self):
        """Close existing SFTP connection."""
        try:
            if self.client:
                self.client.close()
                self.client = None
            if self.transport:
                self.transport.close()
                self.transport = None
            logger.debug("SFTP connection closed successfully.")
        except Exception as e:
            logger.exception(f"Error closing SFTP connection: {e}")

    def reconnect(self):
        """Reconnect to the SFTP server."""
        logger.debug("Attempting to reconnect to SFTP server...")
        try:
            self.disconnect()
            return self.connect()
        except Exception as e:
            logger.exception(f"Failed to reconnect to SFTP server: {e}")
            raise RuntimeError(f"Failed to reconnect to SFTP server: {e}")
        
    @retry_sftp_operation
    def list_remote_dir(self, remote_path):
        """List contents of a remote directory, filtering by exclusion rules."""
        cutoff_time = datetime.now() - timedelta(minutes=1)
        fetched_at = datetime.now()

        entries = []
        remote_path = remote_path.replace('\\', '/')
        for attr in self.client.listdir_attr(remote_path):
            name = attr.filename
            path = remote_path.rstrip('/') + '/' + name.replace('\\', '/')
            is_dir = stat.S_ISDIR(attr.st_mode)
            modified_time = datetime.fromtimestamp(attr.st_mtime)

            # Skip files modified in the last minute
            if modified_time > cutoff_time:
                continue

            # Skip invalid media files and directories with excluded keywords
            if is_dir:
                if not is_valid_directory(name):
                    continue
            else:
                if not is_valid_media_file(name):
                    continue

            entries.append({
                "name": name,
                "remote_path": path,
                "size": attr.st_size,
                "modified_time": modified_time,
                "is_dir": is_dir,
                "fetched_at": fetched_at
            })

        logger.debug(f"Listed {len(entries)} entries in {remote_path}")
        return entries

    @retry_sftp_operation
    def list_remote_files(self, remote_path):
        """Return a list of recursively listed files from the remote path."""
        excluded_extensions = {"jpg", "jpeg", "png", "gif", "bmp", "nfo", "sfv"}
        excluded_keywords = {"screens", "sample", "Thumbs.db", ".DS_Store"}
        cutoff_time = datetime.now() - timedelta(minutes=1)
        fetched_at = datetime.now()
        
        entries = []
        remote_path = remote_path.replace('\\', '/')
        for entry in self.client.listdir_attr(remote_path):
            name = entry.filename
            path = remote_path.rstrip('/') + '/' + name.replace('\\', '/')
            is_dir = stat.S_ISDIR(entry.st_mode)
            ext = os.path.splitext(name)[1][1:].lower()
            lower_name = name.lower()
            modified_time = datetime.fromtimestamp(entry.st_mtime)
            
            if is_dir:
                if not is_valid_directory(lower_name):
                    continue
            else:
                if not is_valid_media_file(lower_name):
                    continue
                
            if modified_time > cutoff_time:
                continue
            
            entries.append({
                "name": name,
                "remote_path": path,
                "size": entry.st_size,
                "modified_time": modified_time,
                "is_dir": is_dir,
                "fetched_at": fetched_at
            })

        logger.debug(f"Listed {len(entries)} entries in {remote_path}")
        return entries

    @retry_sftp_operation
    def _list_remote_files_recursive_helper(self, remote_path, entries):
        """Helper method for recursive file listing."""
        cutoff_time = datetime.now() - timedelta(minutes=1)
        fetched_at = datetime.now()

        remote_path = remote_path.replace('\\', '/')
        for attr in self.client.listdir_attr(remote_path):
            name = attr.filename
            path = remote_path.rstrip('/') + '/' + name.replace('\\', '/')
            is_dir = stat.S_ISDIR(attr.st_mode)
            modified_time = datetime.fromtimestamp(attr.st_mtime)

            # Skip files modified in the last minute
            if modified_time > cutoff_time:
                continue

            # For directories, recurse
            if is_dir:
                self._list_remote_files_recursive_helper(path, entries)
                continue

            # Skip invalid media files
            if not is_valid_media_file(name):
                continue

            entries.append({
                "name": name,
                "remote_path": path,
                "size": attr.st_size,
                "modified_time": modified_time,
                "is_dir": False,
                "fetched_at": fetched_at
            })
        logger.debug(f"Listed {len(entries)} files in {remote_path}")

    @retry_sftp_operation
    def list_remote_files_recursive(self, remote_path):
        """Return a list of recursively listed files from the remote path.
        
        This method will list all files and directories within the given path,
        except those excluded by is_valid_media_file().
        """
        entries = []
        remote_path = remote_path.replace('\\', '/')
        self._list_remote_files_recursive_helper(remote_path, entries)
        logger.debug(f"Listed {len(entries)} entries in {remote_path}")
        return entries

    def _truncate_filename(self, fname, llm_service, max_path_length, local_base, truncated_dir_name):
        """
        Truncate a filename to fit within max_path_length when combined with the local_base and truncated_dir_name.
        Uses LLM if available, then regex parsing, then fallback truncation.
        """
        # Try LLM for filename truncation first if available
        if llm_service:
            base_name = llm_service.suggest_short_filename(fname, max_length=max_path_length - len(os.path.abspath(os.path.join(local_base, truncated_dir_name, ''))))
            logger.debug(f"LLM suggested filename: {base_name} for original: {fname}")
            if len(os.path.abspath(os.path.join(local_base, truncated_dir_name, base_name))) <= max_path_length:
                return base_name
        # Fallback to regex parsing
        parser_result = parse_filename(fname, llm_service=llm_service)
        extension = os.path.splitext(fname)[1][1:].lower()
        if parser_result.get('show_name') and parser_result.get('season') and parser_result.get('episode'):
            base_name = f"{parser_result['show_name']}.S{parser_result['season']}E{parser_result['episode']}.{extension}"
            if len(os.path.abspath(os.path.join(local_base, truncated_dir_name, base_name))) > max_path_length:
                show = parser_result['show_name']
                show_short = show[:10]
                base_name = f"{show_short}.S{parser_result['season']}E{parser_result['episode']}.{extension}"
            return base_name
        elif parser_result.get('show_name') and parser_result.get('episode'):
            base_name = f"{parser_result['show_name']}.E{parser_result['episode']}.{extension}"
            if len(os.path.abspath(os.path.join(local_base, truncated_dir_name, base_name))) > max_path_length:
                show = parser_result['show_name']
                show_short = show[:10]
                base_name = f"{show_short}.E{parser_result['episode']}.{extension}"
            return base_name
        # fallback: just truncate filename
        base_name = fname[:max(1, max_path_length - len(os.path.abspath(os.path.join(local_base, truncated_dir_name, ''))))]
        return base_name

    def _truncate_for_windows_path(self, local_base, dir_name, remote_path, max_path_length=250):
        """
        Given a local base path, a directory name, and the remote path, determine if truncation is needed for the directory and/or filenames so that all resulting paths are <= max_path_length (default 250 chars).
        Returns (truncated_dir_name, filename_map) where filename_map is {original: truncated} or None if not needed.
        """
        entries = []
        self._list_remote_files_recursive_helper(remote_path, entries)
        filenames = [entry['name'] for entry in entries if not entry.get('is_dir', False)]
        truncated_dir_name = dir_name
        filename_map = None

        # Initial check: is any path too long with the original dir name?
        max_path = max((len(os.path.abspath(os.path.join(local_base, dir_name, fname))) for fname in filenames), default=0)
        if max_path <= max_path_length:
            logger.debug(f"No truncation needed for dir {dir_name} in {local_base}")
            return truncated_dir_name, None

        # Find the longest filename
        max_filename_length = max((len(fname) for fname in filenames), default=0)
        # Calculate max allowed dirname length
        max_dirname_length = max_path_length - max_filename_length - len(os.path.abspath(os.path.join(local_base, ''))) - 1

        # Try truncating the directory name (always try LLM if available)
        if self.llm_service:
            truncated_dir_name = self.llm_service.suggest_short_dirname(dir_name, max_length=max_dirname_length)
        else:
            truncated_dir_name = dir_name[:max_dirname_length]

        # Check again: is any path too long with the truncated dir name?
        max_path = max((len(os.path.abspath(os.path.join(local_base, truncated_dir_name, fname))) for fname in filenames), default=0)
        if max_path <= max_path_length:
            logger.debug(f"Truncated dir name to {truncated_dir_name} in {local_base}")
            return truncated_dir_name, None

        # Only now, if still too long, parse and truncate filenames
        filename_map = {}
        for fname in filenames:
            base_name = self._truncate_filename(fname, self.llm_service, max_path_length, local_base, truncated_dir_name)
            filename_map[fname] = base_name
        logger.debug(f"Truncated filenames for dir {truncated_dir_name} in {local_base}")
        return truncated_dir_name, filename_map

    @retry_sftp_operation
    def download_dir(self, remote_path, local_path, filename_map=None, max_workers=4):
        """
        Download all files and subdirectories in a directory in parallel using a thread pool.
        Each file/subdir download uses a new SFTPService instance.
        Preserves filename mapping for path truncation.
        """
        remote_path = remote_path.replace('\\', '/')
        dir_name = os.path.basename(remote_path.rstrip('/'))
        parent_path = os.path.dirname(local_path)
        # If this is a recursive call, use the provided filename_map and local_path (already truncated)
        # Otherwise, compute truncation and filename mapping for this directory
        if filename_map is not None:
            truncated_dir_name = os.path.basename(local_path)
            new_filename_map = filename_map
        else:
            # Compute truncation and filename mapping for the top-level directory
            truncated_dir_name, new_filename_map = self._truncate_for_windows_path(parent_path, dir_name, remote_path)
            local_path = os.path.join(parent_path, truncated_dir_name)
        os.makedirs(local_path, exist_ok=True)

        # Gather files and subdirectories for parallel download
        files_info = []
        subdirs = []
        fetched_at = datetime.now()
        for entry in self.client.listdir_attr(remote_path):
            # Always use forward slashes for remote paths
            remote_entry = remote_path.rstrip('/') + '/' + entry.filename.replace('\\', '/')
            if stat.S_ISDIR(entry.st_mode):
                # Apply directory filtering
                if not is_valid_directory(entry.filename):
                    logger.debug(f"Skipping directory due to filter: {entry.filename}")
                    continue
                # For each subdirectory, precompute its truncation and filename mapping
                subdir_local_path = os.path.join(local_path, entry.filename)
                subdir_trunc_name, subdir_filename_map = self._truncate_for_windows_path(local_path, entry.filename, remote_entry)
                subdir_local_path = os.path.join(local_path, subdir_trunc_name)
                # Pass the mapping and truncated name to the parallel task
                subdirs.append((remote_entry, subdir_local_path, subdir_filename_map))
            else:
                # Apply file filtering
                if not is_valid_media_file(entry.filename):
                    logger.debug(f"Skipping file due to filter: {entry.filename}")
                    continue
                # Use the filename mapping for this directory if present
                local_filename = new_filename_map[entry.filename] if new_filename_map and entry.filename in new_filename_map else entry.filename
                files_info.append({
                    "remote_entry": remote_entry,
                    "local_file": os.path.join(local_path, local_filename),
                    "size": entry.st_size,
                    "modified_time": datetime.fromtimestamp(entry.st_mtime),
                    "name": entry.filename,
                    "is_dir": False,
                    "fetched_at": fetched_at,
                })

        # Prepare SFTP connection parameters for new instances (each thread gets its own connection)
        sftp_params = {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "ssh_key_path": self.ssh_key_path,
            "llm_service": self.llm_service,
        }

        # Task for downloading a single file (runs in a thread)
        def file_download_task(remote_entry, local_file):
            logger.info(f"Starting download of file: {remote_entry} -> {local_file}")
            sftp = SFTPService(**sftp_params)
            with sftp:
                sftp.download_file(remote_entry, local_file)
            logger.info(f"Completed download of file: {remote_entry} -> {local_file}")

        # Task for downloading a subdirectory (runs in a thread, recurses in parallel)
        def dir_download_task(remote_entry, local_dir, subdir_filename_map):
            sftp = SFTPService(**sftp_params)
            with sftp:
                # Recursively call download_dir with the correct filename mapping for this subdir
                return sftp.download_dir(
                    remote_entry,
                    local_dir,
                    filename_map=subdir_filename_map,
                    max_workers=max_workers,
                )

        # Use a thread pool to download all files and subdirectories in parallel
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_kind = {}
            # Submit all file download tasks
            for info in files_info:
                fut = executor.submit(file_download_task, info["remote_entry"], info["local_file"])
                future_to_kind[fut] = ("file", info)
            # Submit all subdirectory download tasks (each will recurse in parallel)
            for remote_entry, local_dir, subdir_filename_map in subdirs:
                fut = executor.submit(dir_download_task, remote_entry, local_dir, subdir_filename_map)
                future_to_kind[fut] = ("dir", None)
            # Wait for all downloads to complete, logging any exceptions
            for future in as_completed(future_to_kind):
                kind, info = future_to_kind[future]
                try:
                    res = future.result()
                    if kind == "file" and info is not None:
                        results.append({
                            "name": info["name"],
                            "remote_path": info["remote_entry"],
                            "size": info["size"],
                            "modified_time": info["modified_time"],
                            "is_dir": False,
                            "fetched_at": info["fetched_at"],
                            "local_path": info["local_file"],
                        })
                    elif kind == "dir" and isinstance(res, list):
                        results.extend(res)
                except Exception as e:
                    logger.exception(f"Failed to download entry in {remote_path}: {e}")

        return results

    @retry_sftp_operation
    def download_file(self, remote_path, local_path, max_path_length=250):
        remote_path = remote_path.replace('\\', '/')
        # Final check for path length
        if len(os.path.abspath(local_path)) > max_path_length:
            logger.warning(f"Local path too long, attempting to truncate filename: {local_path}")
            dir_path = os.path.dirname(local_path)
            orig_filename = os.path.basename(local_path)
            dir_name = os.path.basename(dir_path)
            base_name = self._truncate_filename(orig_filename, self.llm_service, max_path_length, os.path.dirname(dir_path), dir_name)
            truncated_path = os.path.join(dir_path, base_name)
            logger.info(f"Truncated filename to: {base_name}")
            local_path = truncated_path
            # Final check again
            if len(os.path.abspath(local_path)) > max_path_length:
                logger.error(f"Skipping file due to path length > 260 after truncation: {local_path}")
                return
        # Always use forward slashes for remote paths
        logger.debug(f"Downloading file from {remote_path} to {local_path}")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        self.client.get(remote_path, local_path)
        logger.debug(f"Downloaded file from {remote_path} to {local_path}")
