import os
from datetime import datetime

# Configuration for nextjs
config = {
    'file_extensions': ['.js', '.jsx', '.ts', '.tsx', '.json'],
    'ignore_directories': ['node_modules', '.git', '.next'],
    'ignore_extensions': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2'],
    'ignore_files': ['package-lock.json', 'yarn.lock'],  # <--- Add your specific files to ignore here
    'output_filename': 'context.txt',
    'max_file_size': 5 * 1024 * 1024,  # 5 MB
    'modified_after': '2024-01-01',    # Include files modified after this date
    'recursive': True
}

def should_ignore_file(file_path):
    # If the file has an extension in ignore_extensions, skip
    if any(file_path.endswith(ext) for ext in config['ignore_extensions']):
        return True

    # If the file is explicitly in ignore_files, skip
    if os.path.basename(file_path) in config['ignore_files']:
        return True

    # If the file size is bigger than max_file_size, skip
    if os.path.getsize(file_path) > config['max_file_size']:
        return True

    # If the file was modified before our cutoff date, skip
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    if file_mod_time < datetime.strptime(config['modified_after'], '%Y-%m-%d'):
        return True

    return False

def write_contents_to_file():
    with open(config['output_filename'], 'w', encoding='utf-8') as output_file:
        for root, dirs, files in os.walk('.', topdown=True):
            # Filter out directories we want to ignore
            dirs[:] = [d for d in dirs if d not in config['ignore_directories']]
            
            for file in files:
                # Only process files that match our listed file extensions
                if any(file.endswith(ext) for ext in config['file_extensions']):
                    file_path = os.path.join(root, file)
                    # Check if we should ignore this file
                    if should_ignore_file(file_path):
                        continue
                    try:
                        # Write the file path
                        output_file.write(f'{file_path}\n')
                        # Then write the contents
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as input_file:
                            file_contents = input_file.read()
                            output_file.write(file_contents + '\n')
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")

if __name__ == '__main__':
    write_contents_to_file()