# config.py
import json
import logging
import os

DEFAULT_CONFIG = {
    # File scanning
    'file_extensions': [
        '.py',
        '.html',
        '.js',
        '.ts',
        '.jsx',
        '.tsx',
        '.tf',
        '.css',
        '.yaml',
        '.json',
        '.toml',
        '.md'
    ],
    'ignore_directories': [
        '__pycache__',
        '.git',
        'venv',
        'env',
        'node_modules',
    ],
    'ignore_extensions': [
        '.png',
        '.jpg',
        '.jpeg',
        '.gif',
        '.svg',
        '.ico',
        '.hcl',
        '.txt'
    ],
    'ignore_patterns': [
        r'.*secret.*',
        r'.*\.log',
    ],
    'modified_after': '2024-01-01',
    'max_file_size': 2 * 1024 * 1024,
    'recursive': True,
    'threads': 8,

    # Output / Behavior
    'output_filename': 'context.txt',
    'compress_output': False,
    'checksum_cache': '.file_checksums.json',
    'use_checksum_cache': False,
    'gather_js_summary': None,

    # Optional scanning overrides
    'explicit_files': [],

    # NEW: Project path & name
    # If project_path is not empty, the script will scan from that path (instead of '.')
    # If project_name is set, we can auto-generate an output file like context_<project_name>.txt
    'project_path': '',
    'project_name': ''
}


def load_config_file(config_path: str) -> dict:
    """
    Loads a configuration from a JSON file.
    Returns an empty dict if the file is missing or invalid.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logging.info(f"Loaded config from: {config_path}")
            return data
    except FileNotFoundError:
        logging.warning(f"Config file {config_path} not found. Skipping.")
    except json.JSONDecodeError as e:
        logging.warning(f"Error parsing JSON in {config_path}: {e}")
    return {}


def merge_configs(base_config: dict, override_config: dict) -> dict:
    """
    Merges override_config into base_config, returning a new config dict.
    For nested lists (like ignore_patterns), we append them.
    """
    merged = base_config.copy()
    for key, value in override_config.items():
        # If it's a list, and the base is also a list, extend it
        if isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key].extend(value)
        else:
            merged[key] = value
    return merged
