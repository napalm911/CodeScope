#!/usr/bin/env python3

import sys
import os
import re
import time
import math
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------
# Configurable Globals
# -------------------
IGNORE_DIRS = {".git", "node_modules", "dist", "build", "__pycache__"}
MAX_FILE_SIZE_MB = 5  # Skip files larger than this many MB
NUM_WORKERS = 8       # Thread pool size (adjust as needed)

# A naive check to see if file might be binary:
# We'll look at a chunk and see if there's a high ratio of non-text bytes.
BINARY_THRESHOLD = 0.3  # If > 30% non-printable in the sample, consider it binary.

# Regex patterns to extract method/function definitions from various languages
# This is *very naive* and can be expanded or refined:
REGEX_PATTERNS = {
    "py": [
        # Python function definition: def function_name(...):
        re.compile(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*\)\s*:", re.MULTILINE),
    ],
    "js": [
        # function myFunc(...) or const myFunc = (...) => { } or let myFunc = () => {}
        re.compile(r"\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*\)", re.MULTILINE),
        re.compile(r"\b(?:const|let)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\(.*?\)\s*=>", re.MULTILINE),
    ],
    "ts": [
        # Similar to JS patterns
        re.compile(r"\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*\)", re.MULTILINE),
        re.compile(r"\b(?:const|let)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\(.*?\)\s*=>", re.MULTILINE),
    ],
    "cpp": [
        # Very naive C++ function signature detection (returnType funcName(...))
        re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_:<>]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*\)", re.MULTILINE),
    ],
    "c": [
        # Similarly naive for C
        re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_*]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*\)", re.MULTILINE),
    ],
    "h": [
        # Headers often contain function declarations
        re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_:<>]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*\)", re.MULTILINE),
    ],
    "lua": [
        # Lua function pattern: function name(...)
        re.compile(r"\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*\)", re.MULTILINE),
    ],
    # Add more patterns for other languages if necessary, e.g. CSS doesn't usually have "functions" in the same sense.
}

def is_ignored_directory(path):
    """
    Check if 'path' ends with one of our ignored directories.
    """
    dir_name = os.path.basename(os.path.normpath(path))
    return dir_name in IGNORE_DIRS

def is_file_too_large(file_path):
    """
    Check if file size is larger than MAX_FILE_SIZE_MB.
    """
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    return file_size_mb > MAX_FILE_SIZE_MB

def looks_like_binary(file_path, chunk_size=1024):
    """
    Check if a file is likely binary by sampling its first chunk.
    If more than BINARY_THRESHOLD portion of the chunk is non-text,
    consider it binary.
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(chunk_size)
        if not chunk:  # empty file
            return False
        # Count how many bytes are "non-printable"
        text_chars = bytearray(range(32,127)) + b'\n\r\t\b'
        non_text_count = sum(byte not in text_chars for byte in chunk)
        ratio = non_text_count / len(chunk)
        return ratio > BINARY_THRESHOLD
    except:
        return True  # If any error, treat as binary

def extract_methods_from_content(content, extension):
    """
    Use naive regex patterns to extract function/method-like definitions.
    Returns a list of strings (method names).
    """
    methods = []
    # Lowercase extension for matching
    ext = extension.lower()
    if ext in REGEX_PATTERNS:
        patterns = REGEX_PATTERNS[ext]
        for pattern in patterns:
            matches = pattern.findall(content)
            methods.extend(matches)
    return methods

def process_file(file_path):
    """
    Processes a single file:
    - Reads the content (if it's small, non-binary)
    - Extracts line_count, char_count, single_line_content
    - Identifies extension
    - Extracts method names
    Returns a dict with file info.
    """
    # Determine extension
    filename = os.path.basename(file_path)
    if '.' in filename:
        extension = filename.split('.')[-1]
    else:
        extension = ''

    # Basic file info dictionary; fill as we go
    file_info = {
        "extension": extension,
        "file_path": file_path,
        "file_name": filename,
        "line_count": 0,
        "char_count": 0,
        "content": "",  # full content if we need it
        "single_line_content": "",
        "methods": []
    }

    # If the file is too large or looks binary, skip reading
    if is_file_too_large(file_path):
        return file_info  # No info beyond extension/file_path
    if looks_like_binary(file_path):
        return file_info  # skip

    # Attempt to read (ignore encoding errors)
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        # If there's an error reading the file, just return partial info
        print(f"[WARN] Could not read file {file_path}: {e}")
        return file_info

    lines = content.splitlines()
    line_count = len(lines)
    char_count = len(content)

    # Single-line content (for GPT usage, etc.)
    single_line_content = content.replace('\n', ' ').replace('\r', ' ')

    # Extract method names based on extension
    methods_found = extract_methods_from_content(content, extension)

    file_info["line_count"] = line_count
    file_info["char_count"] = char_count
    file_info["content"] = content  # We keep the full content for the "human-readable" report
    file_info["single_line_content"] = single_line_content
    file_info["methods"] = methods_found

    return file_info


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 enhanced_audit.py <directory_path>")
        sys.exit(1)

    directory = sys.argv[1]

    # Validate the directory
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory.")
        sys.exit(1)

    # Make sure the output directory exists
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Let's collect all file paths first so we can show progress
    file_paths = []
    for root, dirs, files in os.walk(directory):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if not is_ignored_directory(os.path.join(root, d))]

        for filename in files:
            file_path = os.path.join(root, filename)
            file_paths.append(file_path)

    total_files = len(file_paths)
    print(f"[INFO] Found {total_files} files to process.\n")

    # We'll store all file info here
    file_info_list = []
    extensions_set = set()

    # Progress stats
    start_time = time.time()
    processed_count = 0

    # Use a ThreadPoolExecutor for concurrency
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        future_to_path = {executor.submit(process_file, fp): fp for fp in file_paths}

        for future in as_completed(future_to_path):
            processed_count += 1
            file_path = future_to_path[future]
            try:
                info = future.result()
                file_info_list.append(info)
                extensions_set.add(info["extension"])
            except Exception as e:
                print(f"[ERROR] Exception processing {file_path}: {e}")

            # Progress logging
            elapsed = time.time() - start_time
            avg_time_per_file = elapsed / processed_count
            remaining = total_files - processed_count
            eta_seconds = remaining * avg_time_per_file
            eta_str = time.strftime("%H:%M:%S", time.gmtime(eta_seconds))

            progress_percent = (processed_count / total_files) * 100
            print(f"[PROGRESS] {processed_count}/{total_files} ({progress_percent:.2f}%) ETA: {eta_str}", end='\r')

    print()  # new line after progress

    # ------------------------
    # Generate existing Reports
    # ------------------------

    # 1) Report on file extensions, plus summary (lines, chars)
    report1_lines = []
    report1_lines.append("=== REPORT 1 ===\n")
    report1_lines.append("File Extensions Found:")
    report1_lines.append("----------------------")
    for ext in sorted(extensions_set):
        if ext == '':
            report1_lines.append("  (no extension)")
        else:
            report1_lines.append(f"  .{ext}")
    report1_lines.append("")

    report1_lines.append("File Summary:")
    report1_lines.append("-------------")
    for info in file_info_list:
        ext_str = f".{info['extension']}" if info['extension'] else "(no extension)"
        report1_lines.append(f"File Name: {info['file_name']}")
        report1_lines.append(f"  Path: {info['file_path']}")
        report1_lines.append(f"  Extension: {ext_str}")
        report1_lines.append(f"  Lines: {info['line_count']}")
        report1_lines.append(f"  Characters: {info['char_count']}")
        report1_lines.append("")

    # 2) Report with files & single-line content (suitable for GPT or other processing)
    report2_lines = []
    report2_lines.append("=== REPORT 2 ===\n")
    report2_lines.append("Files With Their Entire Content on One Line:")
    report2_lines.append("--------------------------------------------")
    for info in file_info_list:
        # e.g. "/path/to/my_file.py: import os print('helloworld')"
        single_line = info['single_line_content']
        # If you prefer, you could limit length or do other formatting
        report2_lines.append(f"{info['file_path']}: {single_line}")

    # ------------------------
    # New Reports: Method Extraction
    # ------------------------

    # 3) Human-Readable: methods/functions found, with minimal formatting
    report3_lines = []
    report3_lines.append("=== REPORT 3 (Human-Readable Methods/Functions) ===\n")
    for info in file_info_list:
        if not info["methods"]:
            continue
        report3_lines.append(f"File: {info['file_path']}")
        report3_lines.append(f"Methods/Functions Found ({len(info['methods'])}):")
        for m in info["methods"]:
            report3_lines.append(f"  - {m}")
        report3_lines.append("")

    # 4) GPT-Focused Report: path + full (original) content (or some truncated version)
    #    If you'd prefer single-line content, just reuse `single_line_content`.
    #    This is basically a raw dump but can be changed as you like.
    report4_lines = []
    report4_lines.append("=== REPORT 4 (GPT-Focused Code Dump) ===\n")
    for info in file_info_list:
        # We'll keep the original multi-line content but you can switch to single-line if needed
        file_header = f"FILE: {info['file_path']}"
        separator = "-" * len(file_header)
        report4_lines.append(file_header)
        report4_lines.append(separator)
        report4_lines.append(info['content'])
        report4_lines.append("\n")  # extra spacing

    # ------------------------
    # Write out the reports
    # ------------------------
    report1_path = os.path.join(output_dir, "report1.txt")
    report2_path = os.path.join(output_dir, "report2.txt")
    report3_path = os.path.join(output_dir, "report3.txt")
    report4_path = os.path.join(output_dir, "report4.txt")

    with open(report1_path, 'w', encoding='utf-8') as f1:
        f1.write("\n".join(report1_lines))

    with open(report2_path, 'w', encoding='utf-8') as f2:
        f2.write("\n".join(report2_lines))

    with open(report3_path, 'w', encoding='utf-8') as f3:
        f3.write("\n".join(report3_lines))

    with open(report4_path, 'w', encoding='utf-8') as f4:
        f4.write("\n".join(report4_lines))

    print("\n[INFO] Audit completed.")
    print("Reports generated:")
    print(f"  {report1_path}")
    print(f"  {report2_path}")
    print(f"  {report3_path}")
    print(f"  {report4_path}")


if __name__ == "__main__":
    main()
