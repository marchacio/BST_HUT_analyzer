import os
from git import Repo
from src.utils import clone_repo, code_analyzer
import sys
import csv
import matplotlib.pyplot as plt

def _create_csv_file(csv_file_path: str, tags: list, analyze_all_file: bool):
    code_data_list = []
    
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        
        # Write the header row
        csv_writer.writerow([
            "Tag",
            "Date",
            "Commit_Author",
            "Type",
            
            '#LoC', 
            '#Files',
                
            "Function_Count", 
            "Async_Function_Count",            
            "Class_Count",
            
            # Security metrics
            "Entropy",
            "Dependencies_Count",
            
            'SAST_findings_count',
            'SAST_findings_high_count',
            'SAST_findings_high',
            'SAST_findings_medium_count',
            'SAST_findings_medium',
            'SAST_findings_low_count',
            'SAST_findings_low',
        ]),
        
        # Salva i dati del commit precedente per calcolare i delta
        previus_tag = None
        
        tag_length = len(tags)

        for i, tag in enumerate(tags):
            
            # Printa l'avanzamento dell'analisi
            print(f"\rAnalizzando il tag {tag.name} ({i+1}/{tag_length})... ", end="")
        
            commit = tag.commit
            
            # Ottieni i dati del commit
            code_data = code_analyzer.code_analyzer_per_commit(commit, analyze_all_file=analyze_all_file)
            
            # Salva i dati del commit corrente nel file CSV
            csv_writer.writerow([
                tag.name,
                commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                commit.author.name,
                
                # add a new column for the type of tag (major, minor, patch, initial)
                "patch" if previus_tag and tag.name.split('.')[0] == previus_tag.split('.')[0] and tag.name.split('.')[1] == previus_tag.split('.')[1] else
                "minor" if previus_tag and tag.name.split('.')[0] == previus_tag.split('.')[0] else
                "major" if previus_tag else "initial",
                
                code_data.get('total_loc', 0), 
                code_data.get('total_files', 0),
                
                code_data.get('function_count', 0),
                code_data.get('async_function_count', 0),
                code_data.get('class_count', 0),
                
                code_data.get('entropy', 0),
                
                code_data.get('dependecies_count', 0),
                
                code_data.get('sast_findings_count', 0),
                
                code_data.get('sast_findings_high_count', 0),
                code_data.get('sast_findings_high', ''),
                code_data.get('sast_findings_medium_count', 0),
                code_data.get('sast_findings_medium', ''),
                code_data.get('sast_findings_low_count', 0),
                code_data.get('sast_findings_low', ''),
            ])
            
            code_data_list.append(code_data)
            previus_tag = tag.name
            
    print(f"\n\nAnalisi completata. I risultati sono stati salvati in {csv_file_path}.")

def analyze_repo(repo: Repo, repo_name: str):
    tags = repo.tags
    if len(tags) < 2:
        print("Non ci sono abbastanza tag per identificare le tendenze.")
        return
        
    # Crea la cartella "analytics/repo_name" se non esiste ed utilizzala come output per i file
    base_path = os.path.join("analytics", repo_name)
    
    # Crea la cartella "analytics" se non esiste
    if not os.path.exists("analytics"):
        os.makedirs("analytics")
    
    # Crea la cartella "analytics/repo_name" se non esiste
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    
    # Ensure the "analytics" directory exists
    os.makedirs(base_path, exist_ok=True)
       
    # Open a CSV file to save the analysis results
    csv_python_file_path = os.path.join(base_path, "python_code_analysis.csv")
    csv_total_file_path = os.path.join(base_path, "all_code_analysis.csv")
    
    _create_csv_file(csv_python_file_path, tags, analyze_all_file=False)
    _create_csv_file(csv_total_file_path, tags, analyze_all_file=True)


if __name__ == "__main__":
    
    # Scarica il repository se non è già presente
    repo_url = sys.argv[1] if len(sys.argv) > 1 else None
    if not repo_url:
        raise ValueError("Please provide the repository URL as the first argument.")
    
    repo = clone_repo.clone_repo(repo_url)
    repo_name = repo_url.rstrip('/').split('/')[-1].split('.git')[0] 
        
    analyze_repo(repo, repo_name)