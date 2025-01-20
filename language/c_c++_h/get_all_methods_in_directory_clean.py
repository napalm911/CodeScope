import re, os, json

def extract_methods(file_path):
    methods = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        regex = re.compile(r'\b(?:[a-zA-Z_][a-zA-Z0-9_:<>]*)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*\)')
        for line in lines:
            line = line.strip()
            match = regex.search(line)
            if match:
                methods.append({"method": match.group(1)})
    except: pass
    return methods

def extract_from_dir(directory):
    data = {}
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.cpp', '.h')):
                methods = extract_methods(os.path.join(root, file))
                if methods: data[file] = methods
    return data

if __name__ == "__main__":
    dir_path = "/home/max/Github/napalm911/otchaos-max/Server/src"
    if os.path.isdir(dir_path):
        result = extract_from_dir(dir_path)
        if result:
            with open("methods.json", 'w', encoding='utf-8') as f:
                json.dump(result, f)
            print("Extraction complete. Results saved to methods.json.")
        else: print("No methods found.")
    else: print(f"Invalid directory: {dir_path}")
