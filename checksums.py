import os
import json
import hashlib
import logging

def load_checksum_cache(cache_path: str) -> dict:
    """
    Loads a JSON dictionary of file->md5 checksums.
    Returns {} if file not found or error.
    """
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Could not load checksum cache {cache_path}: {e}")
        return {}


def save_checksum_cache(cache_path: str, cache_dict: dict):
    """
    Saves the dictionary of checksums to a JSON file.
    """
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_dict, f, indent=2)
    except Exception as e:
        logging.warning(f"Could not save checksum cache {cache_path}: {e}")


def compute_md5(file_path: str) -> str:
    """
    Computes the MD5 checksum of a file.
    """
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()
