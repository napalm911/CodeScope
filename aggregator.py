# aggregator.py

import os
import gzip
import json
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from checksums import load_checksum_cache, save_checksum_cache, compute_md5
from file_scanner import should_ignore_file, collect_file_candidates
from js_parser import gather_js_ts_summary
from config import DEFAULT_CONFIG

def read_file_content(file_path: str, config: dict, checksum_cache: dict) -> tuple:
    if config['use_checksum_cache']:
        file_md5 = compute_md5(file_path)
        checksum_cache[file_path] = file_md5

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    return file_path, content

def collect_and_write_context(config: dict):
    # Step 1: Potentially rename the output file if project_name is set
    if config['project_name'] and config['output_filename'] == DEFAULT_CONFIG['output_filename']:
        config['output_filename'] = f"context_{config['project_name']}.txt"
        logging.info(f"Auto-generated output filename: {config['output_filename']}")

    # Step 2: Create subfolder structure in output_folder
    # Default to "output" if not set
    output_folder = config.get('output_folder', 'output')
    if config['project_name']:
        output_folder = os.path.join(output_folder, config['project_name'])

    # Ensure the folder exists
    os.makedirs(output_folder, exist_ok=True)

    # 3) Load or init checksum cache
    if config['use_checksum_cache']:
        checksum_cache = load_checksum_cache(config['checksum_cache'])
    else:
        checksum_cache = {}

    # 4) Gather file candidates
    file_candidates = collect_file_candidates(config)
    logging.info(f"Collected {len(file_candidates)} candidate files.")

    # 5) Filter them
    logging.info("Filtering files...")
    filtered_files = []
    for fpath in file_candidates:
        if not should_ignore_file(fpath, config, checksum_cache):
            filtered_files.append(fpath)
    logging.info(f"{len(filtered_files)} files remain after filtering.")

    # 6) Read them in parallel
    logging.info("Reading file contents...")
    results = []
    with ThreadPoolExecutor(max_workers=config['threads']) as executor:
        future_map = {
            executor.submit(read_file_content, fpath, config, checksum_cache): fpath
            for fpath in filtered_files
        }
        for fut in as_completed(future_map):
            original_fp = future_map[fut]
            try:
                results.append(fut.result())
            except Exception as e:
                logging.warning(f"Error reading {original_fp}: {e}")

    # 7) Build final output path
    final_output_path = os.path.join(output_folder, config['output_filename'])

    # If compress, .gz appended
    if config['compress_output']:
        final_output_path += '.gz'
        open_fn = gzip.open
        open_mode = 'wt'
        logging.info(f"Output will be compressed at: {final_output_path}")
    else:
        open_fn = open
        open_mode = 'w'
        logging.info(f"Output file: {final_output_path}")

    # 8) Write to output
    with open_fn(final_output_path, open_mode, encoding='utf-8') as outfile:
        for (fp, content) in results:
            outfile.write(fp + '\n')
            outfile.write(content + '\n')

    # 9) Save checksums
    if config['use_checksum_cache']:
        save_checksum_cache(config['checksum_cache'], checksum_cache)

    # 10) Gather JS summary if requested
    if config['gather_js_summary']:
        js_summary_path = os.path.join(output_folder, config['gather_js_summary'])
        logging.info(f"Gathering JS/TS summary into {js_summary_path}...")

        project_path = config.get('project_path', '.') or '.'
        summary_list = gather_js_ts_summary(Path(project_path))

        with open(js_summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary_list, f, indent=2)

        logging.info("JS/TS summary generated.")

    logging.info("Done!")
