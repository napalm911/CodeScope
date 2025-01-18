#!/usr/bin/env python3

import os
import re
import json
import sys
from pathlib import Path

# Regex patterns for detecting imports/requires and function/class definitions
IMPORT_PATTERN = re.compile(r'^\s*import\s+(?:[\w*\s{},]+from\s+)?["\']([^"\']+)["\']', re.MULTILINE)
REQUIRE_PATTERN = re.compile(r'\brequire\s*\(\s*["\']([^"\']+)["\']\s*\)')
FUNCTION_PATTERN = re.compile(r'(?:export\s+)?function\s+([\w$]+)\s*\(', re.MULTILINE)
CLASS_PATTERN = re.compile(r'(?:export\s+)?class\s+([\w$]+)\s*\{', re.MULTILINE)

def parse_javascript_file(file_path: Path):
    """
    Parse a JS/TS file to:
      - Extract import/require sources
      - Extract named function and class definitions
      - Log how many lines are read, how many are 'context lines',
        and how many are 'skipped lines' (inside function/class bodies).

    Returns a dict summarizing the info.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    imports = []
    requires = []
    functions = []
    classes = []

    total_lines = len(lines)
    context_lines = 0
    skipped_lines = 0

    # We'll iterate line by line, tracking whether we are inside a function/class block.
    # This is naive. We track curly braces once we see a function or class signature,
    # and keep skipping lines until braces close.
    inside_block = False
    block_brace_count = 0

    # For capturing aggregated text if needed
    # but here we'll just skip them from context.
    
    # Pre-compile single-line regexes we can apply per line:
    import_line_regex = re.compile(r'^\s*import\s+(?:[\w*\s{},]+from\s+)?["\']([^"\']+)["\']')
    require_line_regex = re.compile(r'\brequire\s*\(\s*["\']([^"\']+)["\']\s*\)')
    function_line_regex = re.compile(r'(?:export\s+)?function\s+([\w$]+)\s*\(')
    class_line_regex = re.compile(r'(?:export\s+)?class\s+([\w$]+)\s*\{')

    def check_if_signature_line(line):
        """
        Check if the line has an import, require, function, or class definition.
        Return a tuple: (found_something, found_import, found_require, found_function, found_class)
        """
        found_import = import_line_regex.search(line)
        found_require = require_line_regex.search(line)
        found_function = function_line_regex.search(line)
        found_class = class_line_regex.search(line)

        found_something = bool(found_import or found_require or found_function or found_class)
        return found_something, found_import, found_require, found_function, found_class

    i = 0
    while i < total_lines:
        line = lines[i]
        # If we are currently inside a block (function or class body) that we want to skip:
        if inside_block:
            skipped_lines += 1
            # Check for '{' or '}' to track nested braces
            open_braces = line.count('{')
            close_braces = line.count('}')
            block_brace_count += open_braces
            block_brace_count -= close_braces

            if block_brace_count <= 0:
                # We've matched the function/class block braces, exit skipping mode
                inside_block = False
                block_brace_count = 0

            i += 1
            continue

        # Not inside a block: check for import/require or function/class signature
        found_something, found_import, found_require, found_function, found_class = check_if_signature_line(line)
        if found_something:
            context_lines += 1

            if found_import:
                imports.append(found_import.group(1))

            if found_require:
                requires.append(found_require.group(1))

            if found_function:
                functions.append(found_function.group(1))
                # We should skip the function body now
                # Attempt to detect the opening '{' in the same line
                # If not found, we look in subsequent lines.
                # Then we'll track braces until they match again.
                # This is naive and might fail for complicated multiline definitions.
                # But let's do a best-effort approach:
                # find the first '{' after the function signature
                brace_index = line.find('{')
                if brace_index == -1:
                    # Move to next line(s) until we find the opening brace
                    open_brace_found = False
                    while i < total_lines and not open_brace_found:
                        i += 1
                        if i >= total_lines:
                            break
                        line = lines[i]
                        skipped_lines += 1  # We consider these lines as inside function definition
                        brace_index = line.find('{')
                        if brace_index != -1:
                            open_brace_found = True
                    if not open_brace_found:
                        # If we never found an opening brace, let's continue scanning
                        continue
                # We found an opening '{' in the current or a subsequent line
                inside_block = True
                block_brace_count = 1  # we have one unmatched '{'
            
            if found_class:
                classes.append(found_class.group(1))
                # Similarly skip the class body
                brace_index = line.find('{')
                if brace_index == -1:
                    # Move to next line(s) until we find the opening brace
                    open_brace_found = False
                    while i < total_lines and not open_brace_found:
                        i += 1
                        if i >= total_lines:
                            break
                        line = lines[i]
                        skipped_lines += 1
                        brace_index = line.find('{')
                        if brace_index != -1:
                            open_brace_found = True
                    if not open_brace_found:
                        # If we never found an opening brace, let's continue
                        continue
                # We found an opening '{'
                inside_block = True
                block_brace_count = 1

            # Move to next line
            i += 1
        else:
            # If it's just a normal line outside any function/class, we count it as read but not context
            i += 1

    file_stats = {
        "file": str(file_path),
        "imports": imports,
        "requires": requires,
        "functions": functions,
        "classes": classes,
        "stats": {
            "total_lines": total_lines,
            "context_lines": context_lines,
            "skipped_lines": skipped_lines,
            "non_context_lines": total_lines - context_lines - skipped_lines
        }
    }

    return file_stats


def gather_js_context(root_directory: Path, output_file: Path = None):
    """
    Recursively walk through the given directory, parse .js and .ts files,
    and gather a list of context objects containing imports, requires, 
    function names, class names, and some code stats.
    """
    context_list = []

    for dirpath, _, filenames in os.walk(root_directory):
        for fname in filenames:
            if fname.endswith(('.js', '.jsx', '.ts', '.tsx')):
                file_path = Path(dirpath) / fname
                file_summary = parse_javascript_file(file_path)
                context_list.append(file_summary)

    # Optionally write to JSON file
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(context_list, f, indent=2)
        print(f"Context information written to: {output_file}")
    else:
        # Otherwise, just print results to stdout
        print(json.dumps(context_list, indent=2))

    return context_list


if __name__ == "__main__":
    """
    Usage:
        python gather_js_context.py /path/to/your/js/project [output.json]
    """
    if len(sys.argv) < 2:
        print("Please provide a root directory for scanning JavaScript/TypeScript files.")
        sys.exit(1)

    root_dir = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    gather_js_context(root_dir, output_path)