import os
import re

EXCLUDED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".nfo", ".sfv"}
EXCLUDED_KEYWORDS = {"sample", "screens", "Thumbs.db", ".DS_Store"}

def is_valid_media_file(filepath: str) -> bool:
    """Returns True if the file is not filtered out by extension or keyword."""
    filename = os.path.basename(filepath).lower()
    if any(kw in filename for kw in EXCLUDED_KEYWORDS):
        return False
    if any(filename.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
        return False
    return True

def sanitize_filename(name: str) -> str:
    """Remove characters that are illegal in file/directory names on most OSes."""
    return re.sub(r'[<>:"/\\|?*]', '', name)