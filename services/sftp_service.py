import paramiko
import logging
import os
import stat
from pathlib import Path
from datetime import datetime
from datetime import timedelta

logger = logging.getLogger(__name__)

class SFTPService:
    def __init__(self, host, port, username, ssh_key_path):
        self.host = host
        self.port = port
        self.username = username
        self.ssh_key_path = ssh_key_path
        self.client = None

    def __enter__(self):
        key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username=self.username, pkey=key)
        self.client = paramiko.SFTPClient.from_transport(transport)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()

    def list_remote_dir(self, remote_path):
        """List contents of a remote directory, filtering by exclusion rules."""
        excluded_extensions = {"jpg", "jpeg", "png", "gif", "bmp", "nfo", "sfv"}
        excluded_keywords = {"screens", "sample", "Thumbs.db", ".DS_Store"}
        cutoff_time = datetime.now() - timedelta(minutes=1)
        fetched_at = datetime.now()

        entries = []
        for attr in self.client.listdir_attr(remote_path):
            name = attr.filename
            path = os.path.join(remote_path, name)
            is_dir = stat.S_ISDIR(attr.st_mode)
            ext = os.path.splitext(name)[1][1:].lower()
            lower_name = name.lower()
            modified_time = datetime.fromtimestamp(attr.st_mtime)

            # Apply filters
            if ext in excluded_extensions:
                continue
            if any(keyword in lower_name for keyword in excluded_keywords):
                continue
            if modified_time > cutoff_time:
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
            
            if ext in excluded_extensions:
                continue
            if any(keyword in lower_name for keyword in excluded_keywords):
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

    def download_file(self, remote_path, local_path):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        self.client.get(remote_path, local_path)
    
    def download_dir(self, remote_path, local_path):
        os.makedirs(local_path, exist_ok=True)
        for entry in self.client.listdir_attr(remote_path):
            remote_entry = f"{remote_path.rstrip('/')}/{entry.filename}"
            local_entry = os.path.join(local_path, entry.filename)

            if stat.S_ISDIR(entry.st_mode):
                self.download_dir(remote_entry, local_entry)
            else:
                self.download_file(remote_entry, local_entry)
