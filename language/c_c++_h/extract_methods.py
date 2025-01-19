import re
import os
import json

def extract_methods(file_path):
    """
    Extracts method definitions and relevant comments from a C++ file.
    
    Args:
        file_path (str): Path to the C++ file.

    Returns:
        list: A list of dictionaries containing method details.
    """
    methods = []

    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # Regex to match function/method definitions
        method_regex = re.compile(r'\b(?:[a-zA-Z_][a-zA-Z0-9_:<>]*)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*\)')

        # Temporary variables to hold method and comment context
        current_comment = []
        for line in lines:
            line = line.strip()

            # Capture comments
            if line.startswith("//"):
                current_comment.append(line.strip("// "))
            elif line.startswith("/*") or line.endswith("*/"):
                current_comment.append(line.strip("/* ").strip("*/"))

            # Check for method definitions
            match = method_regex.search(line)
            if match:
                method_name = match.group(1)
                methods.append({
                    "method": method_name,
                    "comments": " ".join(current_comment)
                })
                current_comment = []  # Reset comments after capturing

    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return methods

if __name__ == "__main__":
    # Replace with the path to your C++ file
    file_path = "luascript.cpp"

    if os.path.exists(file_path):
        methods = extract_methods(file_path)
        if methods:
            # Save methods to a JSON file
            output_file = "methods.json"
            try:
                with open(output_file, 'w') as json_file:
                    json.dump(methods, json_file, indent=4)
                print(f"Extracted methods and comments have been saved to '{output_file}'.")
            except Exception as e:
                print(f"An error occurred while writing to JSON file: {e}")
        else:
            print("No methods found in the file.")
    else:
        print(f"The file '{file_path}' does not exist. Please provide a valid path.")