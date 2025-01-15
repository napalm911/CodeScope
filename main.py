#!/usr/bin/env python3
"""
UNIFIED CONTEXT SCRIPT

Combines:
  - Enhanced context generation (originally in context.py)
  - JavaScript/TypeScript parsing to gather project context 
    (originally in typescript.py + gather_js_context.py)

Usage Examples:
  1) Basic usage to gather all file contents (code context + JS/TS structure):
       python unified_context.py --output context.txt

  2) Compress the output:
       python unified_context.py --compress

  3) Only include files modified after 2025-01-01:
       python unified_context.py --modified-after 2025-01-01

  4) Include JS/TS function/class/prototype definitions in a JSON summary:
       python unified_context.py --gather-js-summary my_js_summary.json

  5) Use checksums to skip unchanged files:
       python unified_context.py --use-checksum

  See "make help" for more usage examples (once you have the provided Makefile).
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
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# -----------------------------------------------------------------------------
# Default Configuration
# -----------------------------------------------------------------------------
DEFAULT_CONFIG = {
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
    'output_filename': 'context.txt', 
    'compress_output': False,         
    'checksum_cache': '.file_checksums.json', 
    'use_checksum_cache': False,      
    'gather_js_summary': None,        
}

# -----------------------------------------------------------------------------
# Additional Patterns to Detect JavaScript/TypeScript Structures
# -----------------------------------------------------------------------------

# Basic imports and requires
IMPORT_PATTERN = re.compile(r'^\s*import\s+(?:[\w*\s{},]+from\s+)?["\']([^"\']+)["\']', re.MULTILINE)
REQUIRE_PATTERN = re.compile(r'\brequire\s*\(\s*["\']([^"\']+)["\']\s*\)', re.MULTILINE)

# Named function and class patterns
FUNCTION_PATTERN = re.compile(r'(?:export\s+)?function\s+([\w$]+)\s*\(', re.MULTILINE)
CLASS_PATTERN = re.compile(r'(?:export\s+)?class\s+([\w$]+)\s*\{', re.MULTILINE)

# NEW: Detect prototype methods like:
#   SomeClass.prototype.someMethod = function(...) { ... }
PROTOTYPE_METHOD_PATTERN = re.compile(
    r'([\w$]+)\.prototype\.([\w$]+)\s*=\s*function\s*\([^)]*\)', 
    re.MULTILINE
)

# -----------------------------------------------------------------------------
# Argument Parsing
# -----------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate a consolidated context file from source code and optionally gather JS/TS structure.'
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
        '--gather-js-summary',
        dest='gather_js_summary',
        type=str,
        help='If given, parse .js/.ts/.jsx/.tsx files to extract classes, functions, imports, requires, prototype methods. Output JSON to this file.'
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
def should_ignore_file(file_path, config, checksum_cache, skip_if_unchanged=False):
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
# JavaScript/TypeScript Parsing
# -----------------------------------------------------------------------------
def parse_javascript_file(file_path: Path):
    """
    Parse a JS/TS file to:
      - Extract import/require sources
      - Extract named function and class definitions
      - Detect prototype method definitions: e.g. SomeClass.prototype.someMethod = function (...)
      - Log how many lines are read, how many are 'context lines',
        and how many are 'skipped lines' (inside function/class bodies).
    Returns a dict summarizing the info.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    total_lines = len(lines)
    context_lines = 0
    skipped_lines = 0

    # Data containers
    imports = []
    requires = []
    functions = []
    classes = []
    prototypes = []  # new: list of (className, methodName)

    # We do a naive approach to skip lines inside blocks once we see a function or class declaration.
    inside_block = False
    block_brace_count = 0

    i = 0
    while i < total_lines:
        line = lines[i]

        # If inside block, track braces to know when block ends
        if inside_block:
            skipped_lines += 1
            # Count braces
            block_brace_count += line.count('{')
            block_brace_count -= line.count('}')
            if block_brace_count <= 0:
                inside_block = False
                block_brace_count = 0
            i += 1
            continue

        # Not inside a block: check for patterns
        # 1) import
        match_import = IMPORT_PATTERN.search(line)
        if match_import:
            imports.append(match_import.group(1))
            context_lines += 1

        # 2) require
        match_require = REQUIRE_PATTERN.search(line)
        if match_require:
            requires.append(match_require.group(1))
            context_lines += 1

        # 3) function
        match_function = FUNCTION_PATTERN.search(line)
        if match_function:
            functions.append(match_function.group(1))
            context_lines += 1
            # Now find the opening brace
            brace_index = line.find('{')
            if brace_index == -1:
                # might be on next lines
                found_open = False
                while i < total_lines and not found_open:
                    i += 1
                    if i >= total_lines:
                        break
                    new_line = lines[i]
                    skipped_lines += 1
                    if '{' in new_line:
                        found_open = True
                        block_brace_count = 1
                        inside_block = True
                i += 1
                continue
            else:
                # We found an opening brace on same line
                inside_block = True
                block_brace_count = 1
            i += 1
            continue

        # 4) class
        match_class = CLASS_PATTERN.search(line)
        if match_class:
            classes.append(match_class.group(1))
            context_lines += 1
            # Now find the opening brace
            brace_index = line.find('{')
            if brace_index == -1:
                # might be on next lines
                found_open = False
                while i < total_lines and not found_open:
                    i += 1
                    if i >= total_lines:
                        break
                    new_line = lines[i]
                    skipped_lines += 1
                    if '{' in new_line:
                        found_open = True
                        block_brace_count = 1
                        inside_block = True
                i += 1
                continue
            else:
                # We found an opening brace
                inside_block = True
                block_brace_count = 1
            i += 1
            continue

        # 5) SomeClass.prototype.someMethod = function (...)
        #    We do not attempt to skip the method body separately, but we can track if it has a '{' on the same line
        match_proto = PROTOTYPE_METHOD_PATTERN.search(line)
        if match_proto:
            class_name = match_proto.group(1)
            method_name = match_proto.group(2)
            prototypes.append(f"{class_name}.{method_name}")
            context_lines += 1
            # Check if there's an opening brace
            brace_index = line.find('{')
            if brace_index == -1:
                # might be on next lines
                found_open = False
                while i < total_lines and not found_open:
                    i += 1
                    if i >= total_lines:
                        break
                    new_line = lines[i]
                    skipped_lines += 1
                    if '{' in new_line:
                        found_open = True
                        block_brace_count = 1
                        inside_block = True
                i += 1
                continue
            else:
                inside_block = True
                block_brace_count = 1
            i += 1
            continue

        # If none matched, just move on
        i += 1

    file_stats = {
        "file": str(file_path),
        "imports": imports,
        "requires": requires,
        "functions": functions,
        "classes": classes,
        "prototype_methods": prototypes,
        "stats": {
            "total_lines": total_lines,
            "context_lines": context_lines,
            "skipped_lines": skipped_lines,
            "non_context_lines": total_lines - context_lines - skipped_lines
        }
    }

    return file_stats


def gather_js_context(root_directory: Path):
    """
    Recursively walk through the given directory, parse .js/.jsx/.ts/.tsx files,
    and gather a list of context objects.
    Returns a list of file summaries.
    """
    context_list = []
    for dirpath, _, filenames in os.walk(root_directory):
        for fname in filenames:
            if fname.endswith(('.js', '.jsx', '.ts', '.tsx')):
                file_path = Path(dirpath) / fname
                summary = parse_javascript_file(file_path)
                context_list.append(summary)
    return context_list

# -----------------------------------------------------------------------------
# File Reading (Generic)
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
    Additionally, if config['gather_js_summary'] is set, we parse 
    JS/TS files for structural info.
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
            full_path = os.path.join(root, file)
            if any(file.endswith(ext) for ext in config['file_extensions']):
                if should_ignore_file(
                    full_path, 
                    config, 
                    checksum_cache, 
                    skip_if_unchanged=config['use_checksum_cache']
                ):
                    continue
                file_tasks.append(full_path)

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
    logging.info("Writing all file contents to output...")
    with open_fn(output_file_path, mode, encoding='utf-8') as output_file:
        for file_path, file_contents in results:
            output_file.write(file_path + '\n')
            output_file.write(file_contents + '\n')

    # Save the updated checksums if using
    if config['use_checksum_cache']:
        save_checksum_cache(config['checksum_cache'], checksum_cache)

    # If user wants a separate JS summary, gather it now
    if config['gather_js_summary']:
        js_summary_path = Path(config['gather_js_summary'])
        logging.info(f"Gathering JS/TS summary to {js_summary_path} ...")
        # We gather from the root '.' or from the same scope where we do the scanning
        # to be consistent with the rest of the script, let's do it from '.' 
        summary_list = gather_js_context(Path('.'))
        with open(js_summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary_list, f, indent=2)
        logging.info("JS/TS summary completed.")

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
    config['gather_js_summary'] = args.gather_js_summary

    # If user specified extra ignore patterns, merge them
    if args.ignore_patterns:
        config['ignore_patterns'].extend(args.ignore_patterns)

    write_contents_to_file(config)

if __name__ == '__main__':
    main()
