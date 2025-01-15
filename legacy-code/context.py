#!/usr/bin/env python3
"""
Enhanced File Context Generator

This script generates a context file consolidating the contents of various files
within a directory tree. It supports command-line arguments, advanced ignoring
patterns, concurrent reading, optional compression, and more.

Examples:
    python context.py --output context.txt --modified-after 2024-01-01
    python context.py --compress --ignore-pattern ".*secret.*"

Author: You :)
"""

import os
import re
import sys
import gzip
import json
import argparse
import hashlib
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# -----------------------------------------------------------------------------
# Default Configuration
# -----------------------------------------------------------------------------
DEFAULT_CONFIG = {
    'file_extensions': [
        '.py',
        '.html',
        '.js',
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

        # Tibia 74 JS Chaos
        'client',
        'data',
        'src',
        'tests',
        'tools'
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
    'ignore_patterns': [  # Regex patterns to ignore in path. Use with care.
        r'.*secret.*',     # Example: any directory or file with "secret" in its path
        r'.*\.log',        # Example: any .log files
    ],
    'modified_after': '2024-01-01',    # Date filter: only read files modified after this date
    'max_file_size': 2 * 1024 * 1024,  # 2 MB
    'recursive': True,
    'threads': 8,                     # Number of threads for concurrent reading
    'output_filename': 'context.txt',  # Default output name
    'compress_output': False,          # If True, will produce context.txt.gz
    'checksum_cache': '.file_checksums.json',  # Cache file for checksums to skip unchanged files
    'use_checksum_cache': False,       # If True, uses (and updates) the checksum cache
}

# -----------------------------------------------------------------------------
# Argument Parsing
# -----------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate a consolidated context file from source code.'
    )
    parser.add_argument(
        '--output',
        dest='output_filename',
        type=str,
        default=DEFAULT_CONFIG['output_filename'],
        help='Name of the output file (e.g., context.txt).'
    )
    parser.add_argument(
        '--compress',
        dest='compress_output',
        action='store_true',
        help='If set, the context file will be compressed using gzip (output .gz).'
    )
    parser.add_argument(
        '--modified-after',
        dest='modified_after',
        type=str,
        default=DEFAULT_CONFIG['modified_after'],
        help='Only include files modified after this date (YYYY-MM-DD).'
    )
    parser.add_argument(
        '--threads',
        dest='threads',
        type=int,
        default=DEFAULT_CONFIG['threads'],
        help='Number of threads to use for concurrent reading.'
    )
    parser.add_argument(
        '--ignore-pattern',
        dest='ignore_patterns',
        action='append',
        help='Regex pattern to ignore. Can be specified multiple times.'
    )
    parser.add_argument(
        '--use-checksum',
        dest='use_checksum_cache',
        action='store_true',
        help='Use MD5 checksums to skip unchanged files (cache stored in .file_checksums.json).'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging.'
    )

    return parser.parse_args()

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(message)s'
    )

# -----------------------------------------------------------------------------
# Checksum Cache Handling
# -----------------------------------------------------------------------------
def load_checksum_cache(cache_path):
    """Load the checksum cache from a JSON file."""
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Could not load checksum cache: {e}")
        return {}

def save_checksum_cache(cache_path, checksum_dict):
    """Save the checksum dictionary to a JSON file."""
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(checksum_dict, f, indent=2)
    except Exception as e:
        logging.warning(f"Could not save checksum cache: {e}")

def compute_md5(file_path):
    """Compute MD5 checksum of a file."""
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

# -----------------------------------------------------------------------------
# File Filtering Logic
# -----------------------------------------------------------------------------
def should_ignore_file(
    file_path, 
    config, 
    checksum_cache, 
    skip_if_unchanged=False
):
    """
    Returns True if the file should be ignored based on:
    - Ignored extensions
    - File size limit
    - Modified date
    - Regex ignore patterns
    - MD5 checksums (optional)
    """
    # 1) Check extension
    if any(file_path.endswith(ext) for ext in config['ignore_extensions']):
        return True
    
    # 2) Check file size
    if os.path.getsize(file_path) > config['max_file_size']:
        return True
    
    # 3) Check modification date
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    if file_mod_time < datetime.strptime(config['modified_after'], '%Y-%m-%d'):
        return True

    # 4) Check regex ignore patterns
    for pattern in config['ignore_patterns']:
        if re.search(pattern, file_path):
            return True

    # 5) If using checksums to skip unchanged files
    if skip_if_unchanged:
        new_md5 = compute_md5(file_path)
        old_md5 = checksum_cache.get(file_path, None)
        if old_md5 is not None and old_md5 == new_md5:
            logging.debug(f"Skipping unchanged file: {file_path}")
            return True

    return False

# -----------------------------------------------------------------------------
# File Reading
# -----------------------------------------------------------------------------
def process_file(file_path, config, checksum_cache):
    """
    Returns a tuple (file_path, file_content) or raises an Exception on failure.
    Also updates the checksum_cache if config['use_checksum_cache'] is True.
    """
    # Compute and update MD5 if configured
    if config['use_checksum_cache']:
        file_md5 = compute_md5(file_path)
        checksum_cache[file_path] = file_md5

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    return file_path, content

# -----------------------------------------------------------------------------
# Main Work
# -----------------------------------------------------------------------------
def write_contents_to_file(config):
    """
    Walk the directory (recursively if config['recursive'] is True),
    gather file contents, and write them to the output file.
    """
    if config['use_checksum_cache']:
        checksum_cache = load_checksum_cache(config['checksum_cache'])
    else:
        checksum_cache = {}

    # Decide on compression or plain text
    if config['compress_output']:
        output_file_path = config['output_filename'] + '.gz'
        open_fn = gzip.open
        mode = 'wt'  # text mode under gzip
        logging.info(f"Output will be compressed into: {output_file_path}")
    else:
        output_file_path = config['output_filename']
        open_fn = open
        mode = 'w'
        logging.info(f"Output file: {output_file_path}")

    file_tasks = []

    logging.info("Collecting file list...")
    for root, dirs, files in os.walk('.', topdown=True):
        # Filter out ignored directories
        dirs[:] = [
            d for d in dirs
            if d not in config['ignore_directories']
            and not any(re.search(p, os.path.join(root, d)) for p in config['ignore_patterns'])
        ]

        for file in files:
            if any(file.endswith(ext) for ext in config['file_extensions']):
                file_path = os.path.join(root, file)
                if should_ignore_file(
                        file_path, 
                        config, 
                        checksum_cache, 
                        skip_if_unchanged=config['use_checksum_cache']
                ):
                    continue

                file_tasks.append(file_path)

    logging.info(f"Found {len(file_tasks)} files to process.")

    # Threaded reading of files
    results = []
    with ThreadPoolExecutor(max_workers=config['threads']) as executor:
        future_to_file = {
            executor.submit(process_file, fp, config, checksum_cache): fp
            for fp in file_tasks
        }
        for future in as_completed(future_to_file):
            fp = future_to_file[future]
            try:
                results.append(future.result())
            except Exception as e:
                logging.warning(f"Error reading {fp}: {e}")

    # Write everything out
    logging.info("Writing to output...")
    with open_fn(output_file_path, mode, encoding='utf-8') as output_file:
        for file_path, file_contents in results:
            output_file.write(file_path + '\n')
            output_file.write(file_contents + '\n')

    # Save the updated checksums if using
    if config['use_checksum_cache']:
        save_checksum_cache(config['checksum_cache'], checksum_cache)

    logging.info("Done!")

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
def main():
    args = parse_args()
    setup_logging(verbose=args.verbose)

    # Merge the default config with the CLI arguments
    config = DEFAULT_CONFIG.copy()
    config['output_filename'] = args.output_filename
    config['compress_output'] = args.compress_output
    config['modified_after'] = args.modified_after
    config['threads'] = args.threads
    config['use_checksum_cache'] = args.use_checksum_cache

    # If user specified extra ignore patterns, merge them
    if args.ignore_patterns:
        config['ignore_patterns'].extend(args.ignore_patterns)

    write_contents_to_file(config)

if __name__ == '__main__':
    main()