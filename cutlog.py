#!/usr/bin/env python3
import os
import sys
import glob

# Define the maximum number of lines to keep per file.
MAX_LINES = 22000

def truncate_file(filepath):
    """
    Truncate the file at 'filepath' to only the first MAX_LINES lines.
    """
    # Read only up to MAX_LINES lines from the file.
    lines_to_keep = []
    with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
        for i, line in enumerate(file):
            if i < MAX_LINES:
                lines_to_keep.append(line)
            else:
                break

    # Write the retained lines back to the file, overwriting the original.
    with open(filepath, 'w', encoding='utf-8', errors='replace') as file:
        file.writelines(lines_to_keep)

def process_log_files(folder_path):
    """
    Process all *.log files in the given folder.
    """
    # Create the search pattern for all *.log files in the folder.
    pattern = os.path.join(folder_path, '*.log')
    log_files = glob.glob(pattern)

    if not log_files:
        print(f"No .log files found in folder: {folder_path}")
        return

    # Process each log file.
    for log_file in log_files:
        print(f"Processing file: {log_file}")
        try:
            truncate_file(log_file)
        except Exception as e:
            print(f"Error processing {log_file}: {e}")

def main():
    # Check if the user provided a folder path.
    if len(sys.argv) != 2:
        print("Usage: python3 script.py /path/to/folder")
        sys.exit(1)

    folder_path = sys.argv[1]

    # Check if the provided folder exists.
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist or is not a directory.")
        sys.exit(1)

    process_log_files(folder_path)

if __name__ == "__main__":
    main()

