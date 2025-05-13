import os
import re
import regex
import sys
from clang import cindex
from sqlite3db import FunctionDB

cindex.Config.set_library_file("/usr/lib/llvm-15/lib/libclang.so.1")

def find_all_c_files(phpsrc_path):
    cmd = f"find {phpsrc_path} -name '*.c' > allcfiles"
    os.system(cmd)
    f = open("./allcfiles", "r")
    allcfiles = f.read().strip('\n').split('\n')
    f.close()
    os.system("rm ./allcfiles")
    return allcfiles

def get_source_text(extent):
    """
    Read and return the text from the file corresponding to the given extent.
    """
    start = extent.start
    end = extent.end
    file_name = start.file.name
    # make sure you have the encoding for non-utf char, otherwise the func range can be wrong!
    with open(file_name, 'r', encoding="iso-8859-1") as f:
        text = f.read()
    # Use the offsets provided by the extent to slice the source text.
    return text[start.offset:end.offset]

def extract_functions(node, functions, main_file):
    # Only process nodes that come from the main file
    if node.location.file and node.location.file.name != main_file:
        return
    # Check if the node is a function declaration and a definition (has a body)
    if node.kind == cindex.CursorKind.FUNCTION_DECL and node.is_definition():
        func_name = node.spelling
        loc = node.location
        try:
            func_content = get_source_text(node.extent)
        except Exception as e:
            func_content = f"Error retrieving content: {e}"
        functions.append({
            'name': func_name,
            'file': loc.file,
            'line': loc.line,
            'column': loc.column,
            'content': func_content
        })
    # Recursively traverse child nodes
    for child in node.get_children():
        extract_functions(child, functions, main_file)

def get_token_number(s):
    # Split the string on whitespace
    tokens = s.split()
    # Return the number of tokens
    return len(tokens)

# Example usage:
if __name__ == "__main__":
    
    # need to modify the following path to extract functions
    
    if not os.path.exists("./data/php-src/php-src"):
        os.system("git clone https://github.com/php/php-src.git ./data/php-src/php-src")
        os.system("cd ./data/php-src/php-src && git checkout 3786cff1f3f3d755f346ade78979976fee92bb48")
    
    os.chdir("./data/php-src/")

    db = FunctionDB("./function-baseline.db")
    phpsrc_path = "./php-src"
    
    allcfiles = find_all_c_files(phpsrc_path)
    count = 0
    for eachcfile in allcfiles:
        c_file_path = eachcfile

        # Create an index to manage the translation units
        index = cindex.Index.create()
        
        # Parse the source file (adjust the arguments as needed, e.g., include paths)
        translation_unit = index.parse(c_file_path, args=['-std=c99'])
        
        functions = []
        extract_functions(translation_unit.cursor, functions, c_file_path)
    
        # Print out all the extracted functions with their content
        print("Extracted Functions:")
        for func in functions:
            count += 1
            print(count)
            filepath = str(func['file'])
            idx = f"{func['file']}:{func['line']}:{func['column']}"
            token_number = get_token_number(func['content'])
            if token_number>=10 and token_number<256:
                db.insert_function(idx, filepath, token_number, func['content'], "-") # baseline test: func['content'].replace(';','; // test',1)
    db.close()


