import os
import re

# TODO: Add more extensions and keywords to the constants
# Always ensure that the constants are lowercase.  Using a set comprehension to ensure uniqueness and lowercasing.
EXCLUDED_EXTENSIONS = {ext.lower() for ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".nfo", ".sfv"}}
EXCLUDED_KEYWORDS = {kw.lower() for kw in {"sample", "screens", "thumbs.db", ".ds_store"}}

# Regex for Illegal characters in file/directory names
ILLEGAL_CHARS_REGEX = re.compile(r'[<>:"/\\|?*]+')

def is_valid_media_file(filepath: str) -> bool:
    """Returns True if the file is valid for download based on extension and keyword rules."""
    filename = os.path.basename(filepath).lower()
    ext = os.path.splitext(filename)[1].lower()

    return not (
        any(keyword in filename for keyword in EXCLUDED_KEYWORDS) or 
        ext in EXCLUDED_EXTENSIONS
    )

def is_valid_directory(dirname: str) -> bool:
    """Returns True if the directory is valid for download based on keyword rules."""
    dirname = os.path.basename(dirname).lower()
    return not any(keyword in dirname for keyword in EXCLUDED_KEYWORDS)
    

def sanitize_filename(name: str) -> str:
    """Remove characters that are illegal in file/directory names on most OSes."""
    return ILLEGAL_CHARS_REGEX.sub('', name)