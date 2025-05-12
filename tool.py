import os
from src.utils import clone_repo, code_analyzer
import csv
import argparse
import time

from src.utils.log import init_logging, log

analyze_all_file = True
sast_analyzer = True
secret_analyzer = True
cyclomatic_analyzer = True

def _create_csv_file(
    csv_file_path: str, 
    tags: list, 
):
    
    code_data_list = []
    
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        
        header = [
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
        ]
        
        # Add SAST and secret analyzer findings to the header if enabled
        if sast_analyzer:
            header += [
                'SAST_findings_count',
                'SAST_findings_high_count',
                'SAST_findings_high',
                'SAST_findings_medium_count',
                'SAST_findings_medium',
                'SAST_findings_low_count',
                'SAST_findings_low',   
            ]
        else:
            log("SAST analyzer is disabled. Skipping SAST findings.")
        
        # Add secret analyzer findings to the header if enabled
        if secret_analyzer:
            header += [
                'Secret_Findings_Count',
                'Secret_Findings_High_Count',
                'Secret_Findings_Medium_Count',
                'Secret_Findings_Low_Count'
            ]
        else:
            log("Secret analyzer is disabled. Skipping secret findings.")
                
        if cyclomatic_analyzer:
            header += [
                'CC_Function_Count',
                'CC_Function_Average',
                'CC_Module_Count',
                'CC_Module_Average',
                'CC_Method_Count',
                'CC_Method_Average',
            ]
        else:
            log("Cyclomatic complexity analyzer is disabled. Skipping cyclomatic complexity findings.")
        
        # Write the header row
        csv_writer.writerow(header),
        
        # Salva i dati del commit precedente per calcolare i delta
        previus_tag = None
        
        tag_length = len(tags)

        for i, tag in enumerate(tags):
            
            # loga l'avanzamento dell'analisi
            log(f"\rAnalizzando il tag {tag.name} ({i+1}/{tag_length})... ")
        
            commit = tag.commit
            
            # Ottieni i dati del commit
            code_data = code_analyzer.code_analyzer_per_commit(
                commit, 
                analyze_all_file=analyze_all_file,
                sast_analyzer=sast_analyzer,
                secret_analyzer=secret_analyzer,
                cyclomatic_complexity_analyzer=cyclomatic_analyzer,
            )
            
            # Salva i dati del commit corrente nel file CSV
            data = [
                tag.name,
                commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                commit.author.name,
                
                # Add a new column for the type of tag (major, minor, patch, initial)
                "patch" if previus_tag and tag.name.split('.')[0] == previus_tag.split('.')[0] and tag.name.split('.')[1] == previus_tag.split('.')[1] else
                "minor" if previus_tag and tag.name.split('.')[0] == previus_tag.split('.')[0] else
                "major" if previus_tag else "initial",
                
                code_data.get('total_loc', 0), 
                code_data.get('total_files', 0),
                
                code_data.get('function_count', 0),
                code_data.get('async_function_count', 0),
                code_data.get('class_count', 0),
                
                code_data.get('entropy', 0),
                
                code_data.get('dependencies_count', 0),
            ]
            
            if sast_analyzer:
                data += [
                    code_data.get('sast_findings_count', 0),
                    code_data.get('sast_findings_high_count', 0),
                    code_data.get('sast_findings_high', ''),
                    code_data.get('sast_findings_medium_count', 0),
                    code_data.get('sast_findings_medium', ''),
                    code_data.get('sast_findings_low_count', 0),
                    code_data.get('sast_findings_low', ''),
                ]
                
            if secret_analyzer:
                data += [
                    # Add secret findings data
                    code_data.get('secret_findings_count', 0),
                    code_data.get('secret_findings_high_count', 0),
                    code_data.get('secret_findings_medium_count', 0),
                    code_data.get('secret_findings_low_count', 0)
                ]
                
            if cyclomatic_analyzer:
                data += [
                    code_data.get('cc_function_count', 0),
                    code_data.get('cc_function_average', 0),
                    code_data.get('cc_module_count', 0),
                    code_data.get('cc_module_average', 0),
                    code_data.get('cc_method_count', 0),
                    code_data.get('cc_method_average', 0),
                ]
            
            
            csv_writer.writerow(data)
            
            code_data_list.append(code_data)
            previus_tag = tag.name
            
    log(f"\n\nAnalisi completata. I risultati sono stati salvati in {csv_file_path}.")

if __name__ == "__main__":
    
    python_csv_name = 'python_code_analysis.csv'
    all_csv_name = 'all_code_analysis.csv'
    
    # Scarica il repository se non è già presente
    parser = argparse.ArgumentParser(
        description="""Analyze a Git repository for code and security metrics.
The analysis includes SAST (Static Application Security Testing), secret detection, cyclomatic complexity, and more.

The results are saved in CSV files for further analysis.
        """,
        usage="python tool.py <repo_url> [options]",
    )
    parser.add_argument("repo_url", type=str, help="The URL of the Git repository to analyze.")
    parser.add_argument("--analyze_all_file", action="store_true", help=f"The script will be run twrice, once for the {python_csv_name} (will analyze only python files) and once for the {all_csv_name} which will include all files without filtering by language.")
    parser.add_argument("--no-sast", action="store_true", help="Disable SAST analyzer. ~20percent faster")
    parser.add_argument("--no-secret", action="store_true", help="Disable secret analyzer. ~15percent faster")
    parser.add_argument("--no-cyclomatic", action="store_true", help="Disable cyclomatic complexity analyzer. ~30percent faster")
    parser.add_argument("--log", action="store_true", help="Save logs to a file.")
    
    args = parser.parse_args()
    
    repo_url = args.repo_url
    analyze_all_file = args.analyze_all_file
    sast_analyzer = not args.no_sast
    secret_analyzer = not args.no_secret
    cyclomatic_analyzer = not args.no_cyclomatic
    
    repo = clone_repo.clone_repo(repo_url)
    repo_name = repo_url.rstrip('/').split('/')[-1].split('.git')[0]
        
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
    
    # inizializza il logger
    init_logging(
        os.path.join(base_path, "log.txt"), 
        save_file=args.log,
    )
    
    # Esegui l'analisi del repository
    tags = repo.tags
    if len(tags) < 2:
        log("Non ci sono abbastanza tag per identificare le tendenze.")
        exit(1)
              
    # Open a CSV file to save the analysis results
    csv_python_file_path = os.path.join(base_path, python_csv_name)
    csv_total_file_path = os.path.join(base_path, all_csv_name)
    
    start_time_python = time.time()
    _create_csv_file(csv_python_file_path, tags)
    end_time_python = time.time()
    log(f"Execution time for Python code analysis: {end_time_python - start_time_python:.2f} seconds")

    if analyze_all_file:
        start_time_total = time.time()
        _create_csv_file(csv_total_file_path, tags)
        end_time_total = time.time()
        log(f"Execution time for total code analysis: {end_time_total - start_time_total:.2f} seconds")