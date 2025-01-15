# **Tool Name: CodeScope**

## **Description**
**CodeScope** is a Python-based tool that provides insights into your codebase by gathering detailed context from source files. It supports JavaScript, TypeScript, Python, and more, extracting meaningful metadata such as imports, functions, classes, and prototype methods. The tool also consolidates file contents, supports advanced filtering, and outputs in plain text or JSON format.

Ideal for analyzing legacy projects, documenting code structures, or ensuring consistency, **CodeScope** includes features like compression, multi-threaded processing, and checksum caching for optimal performance.

---

## **Features**
- **File Consolidation:** Reads files of configurable extensions and writes their contents to a single output file.
- **JS/TS Analysis:** Extracts metadata such as imports, requires, functions, classes, and prototype methods into a structured JSON summary.
- **Advanced Filtering:** Supports filters based on size, modification date, directory, and regex patterns.
- **Compression Support:** Compress output using gzip for efficient storage.
- **Multi-threaded Performance:** Uses concurrent file reading for faster processing.
- **Checksum Caching:** Skips unchanged files using MD5-based caching for incremental runs.
- **Makefile Integration:** Simplifies usage with predefined commands.

---

## **Installation**
1. Clone the repository:
   ```bash
   git clone https://github.com/napalm911/CodeScope.git
   cd CodeScope
   ```
2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

---

## **Usage**
### Basic Commands
Run the tool directly:
```bash
poetry run python unified_context.py --output context.txt
```

Compress the output:
```bash
poetry run python unified_context.py --compress --output context.txt.gz
```

Generate a JSON summary of JavaScript/TypeScript structure:
```bash
poetry run python unified_context.py --gather-js-summary js_summary.json
```

Filter files modified after a specific date:
```bash
poetry run python unified_context.py --modified-after 2025-01-01 --output recent_context.txt
```

### Using the Makefile
The tool includes a Makefile for easier execution:
```bash
make help              # Display available commands
make run-all           # Gather all context into context.txt
make run-compressed    # Same as above but compresses the output
make run-js-summary    # Generate JS/TS structure summary in js_summary.json
make clean             # Remove generated output files
```

Example:
```bash
make run-js-summary
```

---

## **Configuration**
Configuration options are in the `DEFAULT_CONFIG` section of the script. Key options include:
- **`file_extensions`**: File types to include (e.g., `.py`, `.js`, `.ts`, etc.).
- **`ignore_directories`**: Directories to exclude (e.g., `node_modules`, `.git`, etc.).
- **`modified_after`**: Include files modified after a given date.
- **`max_file_size`**: Maximum size of files to process.
- **`compress_output`**: Option to gzip-compress output files.
- **`use_checksum_cache`**: Enable caching for faster incremental runs.

---

## **Example Output**
### Text Output
```plaintext
client/src/__proto__.js
"use strict"

String.prototype.capitalize = function () { ... }
Function.prototype.TRUE = function () { ... }
...
```

### JSON Summary
```json
[
  {
    "file": "client/src/__proto__.js",
    "imports": [],
    "requires": [],
    "functions": [],
    "classes": [],
    "prototype_methods": [
      "String.capitalize",
      "Function.TRUE"
    ],
    "stats": {
      "total_lines": 100,
      "context_lines": 50,
      "skipped_lines": 25,
      "non_context_lines": 25
    }
  }
]
```

---

## **Contributing**
1. Fork the repository.
2. Create a feature branch: `git checkout -b feature-name`.
3. Commit your changes: `git commit -m 'Add a new feature'`.
4. Push to your branch: `git push origin feature-name`.
5. Submit a pull request.

---

## **License**
This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## **Credits**
Developed by **Max** and the open-source community. 🚀
