from git import Commit
from src.utils.shannon_entropy import calculate_shannon_entropy
from src.utils.sast_analyzer import analyze_python_file_for_sast
import ast

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
                # Gestisce importazioni come 'import module1, module2 as m2'
                for alias in node.names:
                    # Ci interessa solo il nome del modulo a livello superiore
                    # es. da 'module1.submodule' prendiamo 'module1'
                    top_level_name = alias.name.split('.')[0]
                    imported_names.add(top_level_name)
            elif isinstance(node, ast.ImportFrom):
                # Gestisce importazioni come 'from package import name' o 'from package.sub import name'
                # Ignora importazioni relative come 'from . import module' (node.level > 0)
                if node.module is not None and node.level == 0:
                    # Ci interessa solo il nome del pacchetto a livello superiore
                    # es. da 'package.subpackage' prendiamo 'package'
                    top_level_name = node.module.split('.')[0]
                    imported_names.add(top_level_name)
                
    except SyntaxError:
        # Handle cases where the code might have syntax errors
        #print("Warning: Could not parse file due to SyntaxError. Skipping function counting for this file.")
        pass
    
    return {
        'function_count': function_count,
        'async_function_count': async_function_count,
        'class_count': class_count,
        'dependecies_set': imported_names,
    }

def code_analyzer_per_commit(commit: Commit, analyze_all_file:bool) -> dict:
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
    
    # Variabile per calcolare l'entropia
    total_bytes = b""
    
    # Set per tenere traccia delle dipendenze
    dependecies = set()
    
    # Lista per tenere traccia dei risultati di SAST (Static Application Security Testing)
    commit_sast_findings = []

    for entry in tree.trees:
        for blob in entry.blobs:
            
            # If the blob is a Python file, count the functions in it
            if analyze_all_file or blob.path.endswith('.py'):
                try:
                    # Get the file content
                    file_content = blob.data_stream.read()
                    
                    # add the content of the file to the total_bytes
                    total_bytes += file_content
                    
                    # Analizza il file corrente e ottieni i findings
                    findings_in_file = analyze_python_file_for_sast(file_content, blob.path)
                    # Aggiungi i findings di questo file alla lista totale
                    commit_sast_findings.extend(findings_in_file)
                    
                    code_data = _read_code_data(file_content)
                    
                    # add the content of the file to the dependecies
                    dependecies.update(code_data['dependecies_set'])
                    
                    final_code_data['function_count'] += code_data['function_count']
                    final_code_data['async_function_count'] += code_data['async_function_count']
                    final_code_data['class_count'] += code_data['class_count']
                    
                    final_code_data['total_loc'] += len(file_content.splitlines())
                    final_code_data['total_files'] += 1
                    
                except Exception as e:
                    print(f"Error processing file {entry.path}: {e}")
                    # Continue to the next file even if one fails
                    pass
                
    entropy = calculate_shannon_entropy(total_bytes)
    final_code_data['entropy'] = entropy
    
    final_code_data['dependecies_count'] = len(dependecies)
    
    
    # Conta i findings per livello di gravità
    high_set = set()
    medium_set = set()
    low_set = set()
    severity_counts = {
        'High': 0,
        'Medium': 0,
        'Low': 0,
    }

    for finding in commit_sast_findings:
        if finding['severity'] in severity_counts: # Aggiungi controllo per sicurezza
            severity_counts[finding['severity']] += 1
            
            # Aggiungi il finding alla lista corrispondente
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
    
    final_code_data['sast_findings_high'] = ", ".join(high_set)
    final_code_data['sast_findings_medium'] = ", ".join(medium_set)
    final_code_data['sast_findings_low'] = ", ".join(low_set)
   
    return final_code_data 