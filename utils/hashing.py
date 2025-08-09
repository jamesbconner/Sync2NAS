"""
Deprecated functional hashing helpers. Use services.hashing_service.HashingService instead.

This module remains for backward compatibility and CLI usage. Internally it delegates
to HashingService with a 1 MiB default chunk size.
"""

from __future__ import annotations

import os
import sys
from services.hashing_service import HashingService


def calculate_crc32(file_path: str, chunk_size: int = 1_048_576) -> str:
    return HashingService(chunk_size=chunk_size).calculate_crc32(file_path)


def calculate_md5(file_path: str, chunk_size: int = 1_048_576) -> str:
    return HashingService(chunk_size=chunk_size).calculate_md5(file_path)


def sha1sum(file_path: str, chunk_size: int = 1_048_576) -> str:
    return HashingService(chunk_size=chunk_size).calculate_sha1(file_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python hashing.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    checksum = calculate_crc32(file_path)
    print(f"[{checksum}]")