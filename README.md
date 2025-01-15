# **CodeScope**

## **Description**
**CodeScope** is a Python-based tool that provides insights into your codebase by gathering detailed context from source files. It supports JavaScript, TypeScript, Python, and more, extracting metadata such as imports, requires, functions, classes, and prototype methods. The tool also consolidates file contents, supports advanced filtering, and outputs in plain text or JSON format.

With features like multi-threaded processing, compression, and MD5 checksum caching, CodeScope is flexible and performant. You can also load or override configurations from a JSON file, allowing you to specify things like explicit file lists, custom ignore patterns, and more.

---

## **Features**
- **File Consolidation:** Reads files (via scanning or from an explicit list) and writes contents to a single output.
- **JS/TS Analysis:** Extracts imports, requires, functions, classes, prototype methods, saved in a structured JSON summary.
- **Advanced Filtering:** Filters by directory, filename patterns, file size, modification date, etc.
- **Compression Support:** Generate gzip-compressed output if desired.
- **Multi-Threaded:** Uses concurrent processing to speed up large codebases.
- **Checksum Caching:** Detects unchanged files to skip re-processing for faster incremental runs.
- **Config File Support:** Load or override defaults from a JSON config file (e.g., `my_config.json`).

---

## **Installation**
1. **Clone the repository**:
   ```bash
   git clone https://github.com/napalm911/CodeScope.git
   cd CodeScope
   ```
2. **Install dependencies** (using Poetry or pip):
   ```bash
   poetry install
   # Or:
   # pip install -r requirements.txt
   ```

---

## **Usage**

### **Basic Commands**

- **Scan and output**:
  ```bash
  python main.py --output context.txt
  ```
- **Compress output**:
  ```bash
  python main.py --compress --output context.txt
  ```
- **JS/TS Summary**:
  ```bash
  python main.py --gather-js-summary js_summary.json
  ```
- **Date Filter**:
  ```bash
  python main.py --modified-after 2025-01-01 --output recent_context.txt
  ```
- **Checksum Caching**:
  ```bash
  python main.py --use-checksum
  ```
- **Load a Config File**:
  ```bash
  python main.py --config-file my_config.json
  ```

### **Using the Makefile**
You can run:
```bash
make help              # Show help
make run-all           # Gather all code context into context.txt
make run-compressed    # Same but gzipped
make run-js-summary    # Gather JS/TS summary to js_summary.json
make clean             # Remove output files
```

---

## **Configuration**
You can modify `DEFAULT_CONFIG` in `config.py`. Or provide a JSON config file (see `--config-file`). Example `my_config.json`:

```json
{
  "file_extensions": [".js", ".ts", ".py"],
  "ignore_directories": ["node_modules", ".git"],
  "ignore_extensions": [".png", ".jpg"],
  "ignore_patterns": ["^build", ".*\\.secret"],
  "explicit_files": ["src/only_this_file.js", "lib/specific_file.py"],
  "modified_after": "2023-01-01",
  "threads": 4,
  "use_checksum_cache": true,
  "gather_js_summary": "my_js_summary.json",
  "output_filename": "my_context.txt"
}
```

When you run:
```bash
python main.py --config-file my_config.json
```
It will merge those overrides into the default configuration.

---

## **Example Output**

### **Plain Text Output**
```
/home/max/CodeScope/client/src/__proto__.js
"use strict"

String.prototype.capitalize = function () { ... }
Function.prototype.TRUE = function () { ... }
...
```

### **JSON Summary**
```json
[
  {
    "file": "/home/max/CodeScope/client/src/__proto__.js",
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
