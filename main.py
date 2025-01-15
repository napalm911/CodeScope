#!/usr/bin/env python3
"""
CodeScope (Refactored with project_path/project_name support)

Usage:
  python main.py --output context.txt
  python main.py --compress
  python main.py --modified-after 2025-01-01
  python main.py --gather-js-summary js_summary.json
  python main.py --use-checksum
  python main.py --config-file my_config.json

JSON config can contain:
  "project_path": "/home/max/my/path"
  "project_name": "MyProject"
  ...
"""

import argparse
import logging

from config import DEFAULT_CONFIG, load_config_file, merge_configs
from aggregator import collect_and_write_context

def parse_command_line_args():
    parser = argparse.ArgumentParser(description='CodeScope: gather code context with optional JS/TS parsing.')
    parser.add_argument('--output', dest='output_filename', type=str,
                        help='Name of the output file (default from config).')
    parser.add_argument('--compress', dest='compress_output', action='store_true',
                        help='Compress the output into .gz.')
    parser.add_argument('--modified-after', dest='modified_after', type=str,
                        help='Include only files modified after this date (YYYY-MM-DD).')
    parser.add_argument('--threads', dest='threads', type=int,
                        help='Number of threads for file reading.')
    parser.add_argument('--ignore-pattern', dest='ignore_patterns', action='append',
                        help='Regex pattern to ignore (can be specified multiple times).')
    parser.add_argument('--use-checksum', dest='use_checksum_cache', action='store_true',
                        help='Use checksums to skip unchanged files.')
    parser.add_argument('--gather-js-summary', dest='gather_js_summary', type=str,
                        help='Output file path for JS/TS summary JSON.')
    parser.add_argument('--config-file', dest='config_file', type=str,
                        help='JSON config file to override defaults.')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging.')

    # We *could* also allow specifying project_path and project_name via CLI:
    # parser.add_argument('--project-path', type=str, help='Path to the project folder.')
    # parser.add_argument('--project-name', type=str, help='Short name for project.')
    return parser.parse_args()

def setup_logger(is_verbose):
    level = logging.DEBUG if is_verbose else logging.INFO
    logging.basicConfig(level=level, format='[%(levelname)s] %(message)s')

def main():
    args = parse_command_line_args()
    setup_logger(args.verbose)

    final_config = DEFAULT_CONFIG.copy()

    # Merge config file if provided
    if args.config_file:
        file_config = load_config_file(args.config_file)
        final_config = merge_configs(final_config, file_config)

    # Merge CLI arguments
    if args.output_filename is not None:
        final_config['output_filename'] = args.output_filename
    if args.compress_output:
        final_config['compress_output'] = True
    if args.modified_after is not None:
        final_config['modified_after'] = args.modified_after
    if args.threads is not None:
        final_config['threads'] = args.threads
    if args.ignore_patterns:
        final_config['ignore_patterns'].extend(args.ignore_patterns)
    if args.use_checksum_cache:
        final_config['use_checksum_cache'] = True
    if args.gather_js_summary:
        final_config['gather_js_summary'] = args.gather_js_summary

    # If you want to allow CLI overrides for project_path or project_name,
    # you'd do something like:
    #
    # if args.project_path:
    #     final_config['project_path'] = args.project_path
    # if args.project_name:
    #     final_config['project_name'] = args.project_name

    collect_and_write_context(final_config)

if __name__ == '__main__':
    main()
