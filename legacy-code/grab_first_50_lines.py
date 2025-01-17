import os
from datetime import datetime

config = {
    'file_extensions': ['.js', '.jsx', '.ts', '.tsx', '.json'],
    'ignore_directories': ['node_modules', '.git', '.next'],
    'ignore_extensions': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2'],
    'ignore_files': ['package-lock.json', 'yarn.lock'],  # same ignore files if you wish
    'output_filename': 'first_50_lines.txt',
    'max_file_size': 5 * 1024 * 1024,  # 5 MB
    'modified_after': '2024-01-01',    # Include files modified after this date
    'recursive': True
}

def should_ignore_file(file_path):
    if any(file_path.endswith(ext) for ext in config['ignore_extensions']):
        return True
    if os.path.basename(file_path) in config['ignore_files']:
        return True
    if os.path.getsize(file_path) > config['max_file_size']:
        return True
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    if file_mod_time < datetime.strptime(config['modified_after'], '%Y-%m-%d'):
        return True
    return False

def write_first_50_lines():
    with open(config['output_filename'], 'w', encoding='utf-8') as output_file:
        for root, dirs, files in os.walk('.', topdown=True):
            dirs[:] = [d for d in dirs if d not in config['ignore_directories']]
            for file in files:
                if any(file.endswith(ext) for ext in config['file_extensions']):
                    file_path = os.path.join(root, file)
                    if should_ignore_file(file_path):
                        continue
                    try:
                        # Write the file path
                        output_file.write(f'{file_path}\n')
                        # Write the first 50 lines of the file
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as input_file:
                            for i, line in enumerate(input_file):
                                if i >= 50:
                                    break
                                output_file.write(line)
                        # Add a newline for clarity between files
                        output_file.write('\n')
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")

if __name__ == '__main__':
    write_first_50_lines()