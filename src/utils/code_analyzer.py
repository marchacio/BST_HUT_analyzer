from git import Commit
from src.utils.shannon_entropy import calculate_shannon_entropy
from src.utils.sast_analyzer import analyze_python_file_for_sast
from src.utils.secret_analyzer import find_secrets_in_file
from src.utils.cyclomatic_complexity_analyzer import analyze_file_complexity
from src.utils.text_metrics_analyzer import analyze_file_text_metrics
import ast

from .log import log

def _read_code_data(code: str) -> dict:
    
    function_count = 0
    async_function_count = 0
    class_count = 0
    
    imported_names = set()
    
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_count += 1
            elif isinstance(node, ast.AsyncFunctionDef):
                async_function_count += 1
            elif isinstance(node, ast.ClassDef):
                class_count += 1
            elif isinstance(node, ast.Import):
                # Handles imports like 'import module1, module2 as m2'
                for alias in node.names:
                    # We are only interested in the top-level module name
                    # e.g., from 'module1.submodule' we take 'module1'
                    top_level_name = alias.name.split('.')[0]
                    imported_names.add(top_level_name)
            elif isinstance(node, ast.ImportFrom):
                # Handles imports like 'from package import name' or 'from package.sub import name'
                # Ignores relative imports like 'from . import module' (node.level > 0)
                if node.module is not None and node.level == 0:
                    # We are only interested in the top-level package name
                    # e.g., from 'package.subpackage' we take 'package'
                    top_level_name = node.module.split('.')[0]
                    imported_names.add(top_level_name)
                
    except SyntaxError:
        # Handle cases where the code might have syntax errors
        #log("Warning: Could not parse file due to SyntaxError. Skipping function counting for this file.")
        pass
    
    return {
        'function_count': function_count,
        'async_function_count': async_function_count,
        'class_count': class_count,
        'dependencies_set': imported_names,
    }

def code_analyzer_per_commit(
    commit: Commit, 
    file_extension:str,
    analyze_all_file:bool,
    sast_analyzer: bool = True,
    secret_analyzer: bool = True,
    cyclomatic_complexity_analyzer: bool = True,
    text_metrics_analyzer: bool = True,
) -> dict:
    """
    Analyzes the code in a commit and returns a dictionary with the number of functions, async functions, and classes.
    
    Args:
        commit (Commit): The commit object to analyze.
        analyze_all_file (bool): If True, analyze all files in the commit. If False, only analyze Python files.
    
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
    
    # Variable to calculate entropy
    total_bytes = b""
    
    # Set to keep track of dependencies
    dependencies = set()
    
    # List to keep track of SAST (Static Application Security Testing) results
    commit_sast_findings = []
    
    # List to keep track of secret analyzer results
    commit_secret_findings = []
    
    # List to keep track of cyclomatic complexity analyzer results
    commit_cyclomatic_complexity_findings = []
    
    total_chars = 0
    total_blank_spaces = 0
    
    for blob in tree.traverse():
        # Skip blobs that are not files
        if blob.type == 'blob' and (analyze_all_file or blob.path.endswith(file_extension)):
            # log(f"Processing file: {blob.path}")
            try:
                # Get the file content
                file_content = blob.data_stream.read()
                
                # add the content of the file to the total_bytes
                total_bytes += file_content
                
                if sast_analyzer:
                    #------------------- SAST Analysis ------------------
                    # Analyze the current file and get the findings
                    findings_in_file = analyze_python_file_for_sast(file_content, blob.path)
                    # Add the findings from this file to the total list
                    commit_sast_findings.extend(findings_in_file)
                    #----------------------------------------------------
                
                if secret_analyzer:
                    #------------------- Secret Analysis ------------------
                    # Analyze the current file and get the secrets
                    secrets_in_file = find_secrets_in_file(file_content, blob.path)
                    # Add the secrets from this file to the total list
                    commit_secret_findings.extend(secrets_in_file)
                    #----------------------------------------------------
                
                if cyclomatic_complexity_analyzer:
                    #------------------- Cyclomatic Complexity Analysis ------------------
                    # Analyze the current file and get the cyclomatic complexity
                    complexity_in_file = analyze_file_complexity(file_content, blob.path)
                    # Add the results from this file to the total list
                    commit_cyclomatic_complexity_findings.extend(complexity_in_file)
                    #---------------------------------------------------------------------
                
                if text_metrics_analyzer:
                    #------------------- Text Metrics Analysis ------------------
                    # Analyze the current file and get the metrics
                    text_metrics = analyze_file_text_metrics(blob.path, file_content.decode('utf-8', errors='replace'))
                    # Add the metrics from this file to the total list
                    if text_metrics['longest_line_length'] > final_code_data.get('longest_line_length', 0):
                        final_code_data['longest_line_length'] = text_metrics['longest_line_length']
                        final_code_data['longest_line_file'] = text_metrics['file']
                        
                    final_code_data['relative_higher_blank_space_ratio'] = max(final_code_data.get('relative_higher_blank_space_ratio', 0), text_metrics['blank_space_ratio'])
                    
                    # Update the totals
                    total_chars += text_metrics['total_chars']
                    total_blank_spaces += text_metrics['total_blank_spaces']
                    #--------------------------------------------------------------
                
                code_data = _read_code_data(file_content)
                
                # add the content of the file to the dependencies
                dependencies.update(code_data['dependencies_set'])
                
                final_code_data['function_count'] += code_data['function_count']
                final_code_data['async_function_count'] += code_data['async_function_count']
                final_code_data['class_count'] += code_data['class_count']
                
                final_code_data['total_loc'] += len(file_content.splitlines())
                final_code_data['total_files'] += 1
                
            except Exception as e:
                log(f"Error processing file {blob.path}: {e}")
                # Continue to the next file even if one fails
                pass
                
    entropy = calculate_shannon_entropy(total_bytes)
    final_code_data['entropy'] = entropy
    
    final_code_data['dependencies_count'] = len(dependencies)
    
    if sast_analyzer:
        
        #-----------------------------------------------
        # SAST findings
        #-----------------------------------------------
        high_set = set()
        medium_set = set()
        low_set = set()
        severity_counts = {
            'High': 0,
            'Medium': 0,
            'Low': 0,
        }

        for finding in commit_sast_findings:
            if finding['severity'] in severity_counts: # Add check for safety
                severity_counts[finding['severity']] += 1
                
                # Add the finding to the corresponding list
                if finding['severity'] == 'High':
                    high_set.add(finding['type'])
                elif finding['severity'] == 'Medium':
                    medium_set.add(finding['type'])
                elif finding['severity'] == 'Low':
                    low_set.add(finding['type'])

        final_code_data['sast_findings_count'] = len(commit_sast_findings)
        final_code_data['sast_findings_high_count'] = severity_counts['High']
        final_code_data['sast_findings_medium_count'] = severity_counts['Medium']
        final_code_data['sast_findings_low_count'] = severity_counts['Low']
        
        final_code_data['sast_findings_high'] = "; ".join(high_set)
        final_code_data['sast_findings_medium'] = "; ".join(medium_set)
        final_code_data['sast_findings_low'] = "; ".join(low_set)
    
    if secret_analyzer:
        #-----------------------------------------------
        # Secret findings
        #-----------------------------------------------
        high_set = set()
        medium_set = set()
        low_set = set()
        severity_counts = {
            'High': 0,
            'Medium': 0,
            'Low': 0,
        }
            
        for finding in commit_secret_findings:
            log(f"[Secret] {finding['file']}:{finding['line']} - {finding['description']} (Type: {finding['type']}) - Match: '{finding['match']}'")
            
            if finding['severity'] in severity_counts: # Add check for safety
                severity_counts[finding['severity']] += 1
                
                # Add the finding to the corresponding list
                if finding['severity'] == 'High':
                    high_set.add(finding['type'])
                elif finding['severity'] == 'Medium':
                    medium_set.add(finding['type'])
                elif finding['severity'] == 'Low':
                    low_set.add(finding['type'])
        
        
        final_code_data['secret_findings_count'] = len(commit_secret_findings)
        final_code_data['secret_findings_high_count'] = severity_counts['High']
        final_code_data['secret_findings_medium_count'] = severity_counts['Medium']
        final_code_data['secret_findings_low_count'] = severity_counts['Low']
    
    if cyclomatic_complexity_analyzer:
        #-----------------------------------------------
        # Cyclomatic Complexity findings
        #-----------------------------------------------
        
        function_set = list()
        module_set = list()
        method_set = list()
        
        for finding in commit_cyclomatic_complexity_findings:
            if finding['type'] == 'function':
                function_set.append(finding['complexity'])
            elif finding['type'] == 'module':
                module_set.append(finding['complexity'])
            elif finding['type'] == 'method':
                method_set.append(finding['complexity'])
        
        final_code_data['cc_function_count'] = len(function_set)
        final_code_data['cc_function_average'] = sum(function_set) / len(function_set) if function_set else 0
        
        final_code_data['cc_module_count'] = len(module_set)
        final_code_data['cc_module_average'] = sum(module_set) / len(module_set) if module_set else 0
        
        final_code_data['cc_method_count'] = len(method_set)
        final_code_data['cc_method_average'] = sum(method_set) / len(method_set) if method_set else 0
            
    if text_metrics_analyzer:
        # Calculate the ratio only if there are total characters to avoid division by zero
        final_code_data['blank_space_ratio'] = total_blank_spaces / total_chars if total_chars > 0 else 0.0
        final_code_data['total_chars'] = total_chars
        final_code_data['total_blank_spaces'] = total_blank_spaces
            
    return final_code_data