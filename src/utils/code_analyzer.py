from git import Commit
import ast

def _read_code_data(code: str) -> dict:
    
    function_count = 0
    async_function_count = 0
    class_count = 0
    
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_count += 1
            elif isinstance(node, ast.AsyncFunctionDef):
                async_function_count += 1
            elif isinstance(node, ast.ClassDef):
                class_count += 1
                
    except SyntaxError:
        # Handle cases where the code might have syntax errors
        #print("Warning: Could not parse file due to SyntaxError. Skipping function counting for this file.")
        pass
    
    return {
        'function_count': function_count,
        'async_function_count': async_function_count,
        'class_count': class_count,
    }

def code_analyzer_per_commit(commit: Commit) -> dict:
    """
    Analyzes the code in a commit and returns a dictionary with the number of functions, async functions, and classes.
    
    Args:
        commit (Commit): The commit object to analyze.
    
    Returns:
        dict: A dictionary containing the counts of functions, async functions, and classes.
    """
    final_code_data = {
        'function_count': 0,
        'async_function_count': 0,
        'class_count': 0,
        
        'total_loc': 0,
        'total_files': 0,
    }
    
    # The commit.files attribute only shows files changed in the commit.
    # To get all files at a commit, we need to traverse the commit's tree.
    tree = commit.tree

    for entry in tree.trees:            
        for blob in entry.blobs:
            # If the blob is a Python file, count the functions in it
            if blob.path.endswith('.py'):
                try:
                    # Get the file content
                    file_content = blob.data_stream.read()
                    
                    code_data = _read_code_data(file_content)
                    
                    final_code_data['function_count'] += code_data['function_count']
                    final_code_data['async_function_count'] += code_data['async_function_count']
                    final_code_data['class_count'] += code_data['class_count']
                    
                    final_code_data['total_loc'] += len(file_content.splitlines())
                    final_code_data['total_files'] += 1
                    
                except Exception as e:
                    print(f"Error processing file {entry.path}: {e}")
                    # Continue to the next file even if one fails
                    pass
                
    return final_code_data 