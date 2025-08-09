"""
HashingService: streaming file hashing with configurable chunk size.

Defaults to a 1 MiB chunk size for large file efficiency.
"""

from __future__ import annotations

import binascii
import hashlib
from typing import Optional


class HashingService:
    """
    Provides streaming hashing operations for large files.

    - CRC32 output is an 8-character uppercase hex string
    - MD5 and SHA1 outputs are lowercase hex strings
    """

    def __init__(self, chunk_size: int = 1_048_576) -> None:
        self.chunk_size = chunk_size

    def calculate_crc32(self, file_path: str) -> str:
        crc = 0
        with open(file_path, "rb") as f:
            while True:
                data = f.read(self.chunk_size)
                if not data:
                    break
                crc = binascii.crc32(data, crc)
        return f"{crc & 0xFFFFFFFF:08X}"

    def calculate_md5(self, file_path: str) -> str:
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            while True:
                data = f.read(self.chunk_size)
                if not data:
                    break
                md5.update(data)
        return md5.hexdigest()

    def calculate_sha1(self, file_path: str) -> str:
        sha1 = hashlib.sha1()
        with open(file_path, "rb") as f:
            while True:
                data = f.read(self.chunk_size)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()


