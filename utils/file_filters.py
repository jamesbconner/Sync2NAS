"""
File and directory filtering utilities for Sync2NAS, including extension/keyword exclusion and filename sanitization.
"""
import os
import re

# TODO: Add more extensions and keywords to the constants
# Always ensure that the constants are lowercase.  Using a set comprehension to ensure uniqueness and lowercasing.
EXCLUDED_EXTENSIONS = {ext.lower() for ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".nfo", ".sfv"}}
EXCLUDED_KEYWORDS = {kw.lower() for kw in {"sample", "screens", "thumbs.db", ".ds_store"}}
EXCLUDED_FILENAMES = {fn.lower() for fn in {"desktop.ini", "thumbs.db", ".DS_Store", "screens", "screenshots", "sample", "samples"}}

# Regex for Illegal characters in file/directory names (excluding path separators)
ILLEGAL_CHARS_REGEX = re.compile(r'[<>:"|?*]+')

# Regex for path separators that should be replaced with spaces
PATH_SEPARATORS_REGEX = re.compile(r'[\\/]+')

def is_valid_media_file(filepath: str) -> bool:
    """
    Returns True if the file is valid for download based on extension and keyword rules.

    Args:
        filepath (str): Path to the file.

    Returns:
        bool: True if file is valid, False otherwise.
    """
    filename = os.path.basename(filepath).lower()
    ext = os.path.splitext(filename)[1].lower()

    return not (
        any(keyword in filename for keyword in EXCLUDED_KEYWORDS) or 
        ext in EXCLUDED_EXTENSIONS
    )

def is_valid_directory(dirname: str) -> bool:
    """
    Returns True if the directory is valid for download based on keyword rules.

    Args:
        dirname (str): Directory name.

    Returns:
        bool: True if directory is valid, False otherwise.
    """
    dirname = os.path.basename(dirname).lower()
    return not any(keyword in dirname for keyword in EXCLUDED_KEYWORDS)
    

def sanitize_filename(name: str) -> str:
    """
    Sanitize filename by intelligently handling illegal characters in file/directory names.
    
    This function handles different scenarios:
    - Replaces illegal characters with spaces to prevent word concatenation
    - Handles path separators (slashes) as word boundaries by replacing with spaces
    - Normalizes multiple consecutive spaces
    - Handles edge cases appropriately
    
    Args:
        name (str): Filename or directory name.
        
    Returns:
        str: Sanitized name with illegal characters replaced by spaces.
    """
    if not name:
        return name
    
    # Replace illegal characters with spaces to prevent word concatenation
    result = ILLEGAL_CHARS_REGEX.sub(' ', name)
    
    # Handle path separators (slashes) as word boundaries by replacing with spaces
    result = PATH_SEPARATORS_REGEX.sub(' ', result)
    
    # Normalize multiple consecutive spaces to single spaces
    result = re.sub(r'\s+', ' ', result)
    
    # Remove leading and trailing spaces
    result = result.strip()
    
    # Handle edge cases where the result might be empty
    if not result:
        return '_'
    
    return result