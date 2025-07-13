"""
Hashing utilities for calculating CRC32, MD5, and SHA1 hashes of files.
"""
import os
import sys
import hashlib
import binascii


def calculate_crc32(file_path: str, chunk_size: int = 65536) -> str:
    """
    Calculate the CRC32 hash of a file.

    Args:
        file_path (str): Path to the file.
        chunk_size (int): Size of chunks to read at a time.

    Returns:
        str: CRC32 hash as an 8-character uppercase hex string.
    """
    crc32 = 0
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            crc32 = binascii.crc32(data, crc32)
    return f"{crc32:08X}"

def calculate_md5(file_path: str) -> str:
    """
    Calculate the MD5 hash of a file.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: MD5 hash as a lowercase hex string.
    """
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()

def sha1sum(file_path: str) -> str:
    """
    Calculate the SHA1 hash of a file.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: SHA1 hash as a lowercase hex string.
    """
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha1.update(chunk)
    return sha1.hexdigest()


if __name__ == "__main__":
    """
    Returns the CRC32 hash of a file.
    This is a simple hash function that can be used to verify the integrity of a file.
    
    Usage: python hashing.py <file_path>
    
    Example: python hashing.py /path/to/file.mp4
    Output: [EC01EB33]
    """
    if len(sys.argv) != 2:
        print("Usage: python hashing.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    checksum = calculate_crc32(file_path)
    print(f"[{checksum}]")