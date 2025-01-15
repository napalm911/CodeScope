# file_scanner.py
import os
import re
import logging
from datetime import datetime
from pathlib import Path

from checksums import compute_md5

def should_skip_directory(dirname: str, config: dict) -> bool:
    # Check exact match first
    if dirname in config['ignore_directories']:
        return True
    # Also check patterns
    for pat in config['ignore_patterns']:
        if re.search(pat, dirname):
            return True
    return False

def should_ignore_file(file_path: str, config: dict, checksum_cache: dict) -> bool:
    """
    Returns True if the file should be ignored based on config rules:
      - Ignored extensions
      - File size limit
      - Modified date
      - Regex ignore patterns
      - MD5 checksums if enabled
    """
    # Extension check
    if any(file_path.endswith(ext) for ext in config['ignore_extensions']):
        return True

    # File size
    if os.path.getsize(file_path) > config['max_file_size']:
        return True

    # Modification date
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    if file_mod_time < datetime.strptime(config['modified_after'], '%Y-%m-%d'):
        return True

    # Regex ignore patterns
    for pattern in config['ignore_patterns']:
        if re.search(pattern, file_path):
            return True

    # Checksum
    if config['use_checksum_cache']:
        new_md5 = compute_md5(file_path)
        old_md5 = checksum_cache.get(file_path)
        if old_md5 is not None and old_md5 == new_md5:
            logging.debug(f"Skipping unchanged file: {file_path}")
            return True

    return False


def collect_file_candidates(config: dict) -> list:
    file_candidates = []
    base_path = config.get('project_path', '') or '.'
    base_path = os.path.abspath(base_path)
    
    for root, dirs, files in os.walk(base_path, topdown=True):
        # Filter out directories based on ignore logic
        dirs[:] = [d for d in dirs if not should_skip_directory(d, config)]
        # Then build file candidates
        for fname in files:
            if any(fname.endswith(ext) for ext in config['file_extensions']):
                full_path = os.path.join(root, fname)
                file_candidates.append(full_path)
    return file_candidates
