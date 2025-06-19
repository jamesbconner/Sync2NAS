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
    def __init__(self, host, port, username, ssh_key_path):
        self.host = host
        self.port = port
        self.username = username
        self.ssh_key_path = ssh_key_path
        self.client = None
        self.transport = None

    def __enter__(self):
        try:
            self.connect()
            return self
        except Exception as e:
            logger.error(f"Error establishing SFTP connection: {e}")
            self.__exit__(None, None, None)
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.client:
                self.client.close()
                self.client = None
        except Exception as e:
            logger.error(f"Error closing SFTP client: {e}")
        
        try:
            if self.transport:
                self.transport.close()
                self.transport = None
        except Exception as e:
            logger.error(f"Error closing transport: {e}")

    def connect(self):
        """Establish a new SFTP connection."""
        try:
            key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
            self.transport = paramiko.Transport((self.host, self.port))
            self.transport.connect(username=self.username, pkey=key)
            self.client = paramiko.SFTPClient.from_transport(self.transport)
            logger.debug(f"SFTP connection established successfully to {self.host}:{self.port}")
            return self
        except Exception as e:
            logger.error(f"Failed to establish SFTP connection to {self.host}:{self.port} with error: {e}")
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
            logger.error(f"Error closing SFTP connection: {e}")

    def reconnect(self):
        """Reconnect to the SFTP server."""
        logger.debug("Attempting to reconnect to SFTP server...")
        try:
            self.disconnect()
            return self.connect()
        except Exception as e:
            logger.error(f"Failed to reconnect to SFTP server: {e}")
            raise RuntimeError(f"Failed to reconnect to SFTP server: {e}")
        
    @retry_sftp_operation
    def list_remote_dir(self, remote_path):
        """List contents of a remote directory, filtering by exclusion rules."""
        cutoff_time = datetime.now() - timedelta(minutes=1)
        fetched_at = datetime.now()

        entries = []
        for attr in self.client.listdir_attr(remote_path):
            name = attr.filename
            path = os.path.join(remote_path, name)
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
                "path": path,
                "size": attr.st_size,
                "modified_time": modified_time,
                "is_dir": is_dir,
                "fetched_at": fetched_at
            })

        return entries

    @retry_sftp_operation
    def list_remote_files(self, remote_path):
        """Return a list of recursively listed files from the remote path."""
        excluded_extensions = {"jpg", "jpeg", "png", "gif", "bmp", "nfo", "sfv"}
        excluded_keywords = {"screens", "sample", "Thumbs.db", ".DS_Store"}
        cutoff_time = datetime.now() - timedelta(minutes=1)
        fetched_at = datetime.now()
        
        entries = []
        for entry in self.client.listdir_attr(remote_path):
            path = os.path.join(remote_path, entry.filename)
            is_dir = stat.S_ISDIR(entry.st_mode)
            ext = os.path.splitext(entry.filename)[1][1:].lower()
            lower_name = entry.filename.lower()
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
                "name": entry.filename,
                "path": path,
                "size": entry.st_size,
                "modified_time": modified_time,
                "is_dir": is_dir,
                "fetched_at": fetched_at
            })

        return entries

    @retry_sftp_operation
    def _list_remote_files_recursive_helper(self, remote_path, entries):
        """Helper method for recursive file listing."""
        cutoff_time = datetime.now() - timedelta(minutes=1)
        fetched_at = datetime.now()

        for attr in self.client.listdir_attr(remote_path):
            name = attr.filename
            path = os.path.join(remote_path, name)
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
                "path": path,
                "size": attr.st_size,
                "modified_time": modified_time,
                "is_dir": False,
                "fetched_at": fetched_at
            })

    @retry_sftp_operation
    def list_remote_files_recursive(self, remote_path):
        """Return a list of recursively listed files from the remote path.
        
        This method will list all files and directories within the given path,
        except those excluded by is_valid_media_file().
        """
        entries = []
        self._list_remote_files_recursive_helper(remote_path, entries)
        return entries

    @retry_sftp_operation
    def download_file(self, remote_path, local_path):
        logger.debug(f"Downloading file from {remote_path} to {local_path}")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        self.client.get(remote_path, local_path)
        logger.debug(f"Downloaded file from {remote_path} to {local_path}")
    
    @retry_sftp_operation
    def download_dir(self, remote_path, local_path):
        os.makedirs(local_path, exist_ok=True)
        for entry in self.client.listdir_attr(remote_path):
            remote_entry = f"{remote_path.rstrip('/')}/{entry.filename}"
            local_entry = os.path.join(local_path, entry.filename)

            if stat.S_ISDIR(entry.st_mode):
                if not is_valid_directory(entry.filename):
                    logger.debug(f"Skipping directory due to filter: {entry.filename}")
                    continue
                logger.debug(f"Downloading directory: {remote_entry}")
                self.download_dir(remote_entry, local_entry)
            else:
                if not is_valid_media_file(entry.filename):
                    logger.debug(f"Skipping file due to filter: {entry.filename}")
                    continue
                logger.debug(f"Downloading file: {remote_entry}")
                self.download_file(remote_entry, local_entry)
