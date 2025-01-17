import os
from datetime import datetime

config = {
    'file_extensions': ['.js', '.jsx', '.ts', '.tsx', '.json'],
    'ignore_directories': ['node_modules', '.git', '.next'],
    'ignore_extensions': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2'],
    'ignore_files': ['package-lock.json', 'yarn.lock'],
    'output_filename': 'file_names.txt',
    'max_file_size': 5 * 1024 * 1024,  # 5 MB
    'modified_after': '2024-01-01',    # Include files modified after this date
    'recursive': True
}

def should_ignore_file(file_path):
    # Check if it matches any "ignore_extensions"
    if any(file_path.endswith(ext) for ext in config['ignore_extensions']):
        return True

    # Check if filename is in "ignore_files"
    if os.path.basename(file_path) in config['ignore_files']:
        return True

    # Check file size
    if os.path.getsize(file_path) > config['max_file_size']:
        return True

    # Check last modified date
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    if file_mod_time < datetime.strptime(config['modified_after'], '%Y-%m-%d'):
        return True

    return False

def write_file_names():
    with open(config['output_filename'], 'w', encoding='utf-8') as output_file:
        for root, dirs, files in os.walk('.', topdown=True):
            # Filter out directories we want to ignore
            dirs[:] = [d for d in dirs if d not in config['ignore_directories']]

            for file in files:
                # Only process files that match our listed file extensions
                if any(file.endswith(ext) for ext in config['file_extensions']):
                    file_path = os.path.join(root, file)

                    if should_ignore_file(file_path):
                        continue

                    # Write the file path (relative to the current directory) to the output file
                    output_file.write(f'{file_path}\n')

if __name__ == '__main__':
    write_file_names()