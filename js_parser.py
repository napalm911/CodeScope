import os
import re
from pathlib import Path

# Regex Patterns for JS/TS Analysis
IMPORT_PATTERN = re.compile(r'^\s*import\s+(?:[\w*\s{},]+from\s+)?["\']([^"\']+)["\']', re.MULTILINE)
REQUIRE_PATTERN = re.compile(r'\brequire\s*\(\s*["\']([^"\']+)["\']\s*\)', re.MULTILINE)
FUNCTION_PATTERN = re.compile(r'(?:export\s+)?function\s+([\w$]+)\s*\(', re.MULTILINE)
CLASS_PATTERN = re.compile(r'(?:export\s+)?class\s+([\w$]+)\s*\{', re.MULTILINE)
PROTOTYPE_METHOD_PATTERN = re.compile(
    r'([\w$]+)\.prototype\.([\w$]+)\s*=\s*function\s*\([^)]*\)',
    re.MULTILINE
)


def parse_js_ts_file(file_path: Path) -> dict:
    """
    Parse a JS/TS file to extract:
      - import/require sources
      - named functions/classes
      - prototype methods
      - basic line stats
    """
    with file_path.open('r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    total_lines = len(lines)
    context_lines = 0
    skipped_lines = 0

    imports = []
    requires = []
    functions = []
    classes = []
    prototypes = []

    inside_block = False
    brace_count = 0
    i = 0

    while i < total_lines:
        line = lines[i]

        if inside_block:
            skipped_lines += 1
            brace_count += line.count('{')
            brace_count -= line.count('}')
            if brace_count <= 0:
                inside_block = False
                brace_count = 0
            i += 1
            continue

        # Check for import
        match_import = IMPORT_PATTERN.search(line)
        if match_import:
            imports.append(match_import.group(1))
            context_lines += 1

        # Check for require
        match_require = REQUIRE_PATTERN.search(line)
        if match_require:
            requires.append(match_require.group(1))
            context_lines += 1

        # Check for function
        match_func = FUNCTION_PATTERN.search(line)
        if match_func:
            functions.append(match_func.group(1))
            context_lines += 1
            if '{' not in line:
                found_open = False
                while i < total_lines and not found_open:
                    i += 1
                    if i >= total_lines:
                        break
                    next_line = lines[i]
                    skipped_lines += 1
                    if '{' in next_line:
                        found_open = True
                        brace_count = 1
                        inside_block = True
                i += 1
                continue
            else:
                inside_block = True
                brace_count = 1
            i += 1
            continue

        # Check for class
        match_class = CLASS_PATTERN.search(line)
        if match_class:
            classes.append(match_class.group(1))
            context_lines += 1
            if '{' not in line:
                found_open = False
                while i < total_lines and not found_open:
                    i += 1
                    if i >= total_lines:
                        break
                    next_line = lines[i]
                    skipped_lines += 1
                    if '{' in next_line:
                        found_open = True
                        brace_count = 1
                        inside_block = True
                i += 1
                continue
            else:
                inside_block = True
                brace_count = 1
            i += 1
            continue

        # Check for prototype method
        match_proto = PROTOTYPE_METHOD_PATTERN.search(line)
        if match_proto:
            class_name, method_name = match_proto.groups()
            prototypes.append(f"{class_name}.{method_name}")
            context_lines += 1
            if '{' not in line:
                found_open = False
                while i < total_lines and not found_open:
                    i += 1
                    if i >= total_lines:
                        break
                    next_line = lines[i]
                    skipped_lines += 1
                    if '{' in next_line:
                        found_open = True
                        brace_count = 1
                        inside_block = True
                i += 1
                continue
            else:
                inside_block = True
                brace_count = 1
            i += 1
            continue

        i += 1

    return {
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


def gather_js_ts_summary(root_dir: Path):
    """
    Walks through root_dir to parse JS/TS files and return a list of summaries.
    """
    summaries = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname.endswith(('.js', '.jsx', '.ts', '.tsx')):
                fpath = Path(dirpath) / fname
                summaries.append(parse_js_ts_file(fpath))
    return summaries
