import os
from datetime import datetime

# Configuration for nextjs
config = {
    'file_extensions': ['.js', '.jsx', '.ts', '.tsx', '.json'],
    'ignore_directories': ['node_modules', '.git', '.next'],
    'ignore_extensions': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2'],
    'output_filename': 'context.txt',
    'max_file_size': 5 * 1024 * 1024,  # 5 MB
    'modified_after': '2024-01-01',  # Include files modified after this date
    'recursive': True
}

# Configuration for python
# config = {
#     'file_extensions': ['.py', '.html', '.jinja2', '.js', '.css'],  # Include relevant extensions
#     'ignore_directories': ['__pycache__', '.git', 'venv', 'env', 'node_modules'],  # Common directories to ignore
#     'ignore_extensions': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico'],  # Ignore non-text files
#     'output_filename': 'context.txt',  # Output file name
#     'max_file_size': 2 * 1024 * 1024,  # 2 MB limit for this example
#     'modified_after': '2024-01-01',  # Example date filter
#     'recursive': True  # Traverse directories recursively
# }


def should_ignore_file(file_path):
    if any(file_path.endswith(ext) for ext in config['ignore_extensions']):
        return True
    if os.path.getsize(file_path) > config['max_file_size']:
        return True
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    if file_mod_time < datetime.strptime(config['modified_after'], '%Y-%m-%d'):
        return True
    return False

def write_contents_to_file():
    with open(config['output_filename'], 'w', encoding='utf-8') as output_file:
        for root, dirs, files in os.walk('.', topdown=True):
            dirs[:] = [d for d in dirs if d not in config['ignore_directories']]  # Modify dirs in-place
            for file in files:
                if any(file.endswith(ext) for ext in config['file_extensions']):
                    file_path = os.path.join(root, file)
                    if should_ignore_file(file_path):
                        continue
                    try:
                        output_file.write(f'{file_path}\n')  # Write the file path
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as input_file:
                            file_contents = input_file.read()
                            output_file.write(file_contents + '\n')  # Write the file contents
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")

if __name__ == '__main__':
    write_contents_to_file()