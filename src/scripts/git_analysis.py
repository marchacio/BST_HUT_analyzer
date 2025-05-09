import os
from git import Repo
from src.utils import clone_repo, code_analyzer
import sys
import csv
import matplotlib.pyplot as plt

def analyze_repo(repo: Repo, repo_name: str):
    tags = repo.tags
    if len(tags) < 2:
        print("Non ci sono abbastanza tag per identificare le tendenze.")
        return
    
    print(f"Numero di tag trovati: {len(tags)}")
    
    # Crea la cartella "analytics" (se non esiste) dalla cartella principale del progetto, ovvero da dove è stato lanciato il codice
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "analytics")
    
    # Ensure the "analytics" directory exists
    os.makedirs(base_path, exist_ok=True)
       
    # Open a CSV file to save the analysis results
    csv_file_path = os.path.join(base_path, "repo_code_analysis.csv")
    
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
            
            'Delta_#LoC',
            'Delta_#Files',
                
            "Function_Count", 
            "Delta_Function_Count", 
            
            "Async_Function_Count",
            "Delta_Async_Function_Count",
            
            "Class_Count",
            "Delta_Class_Count",
            
            # Security metrics
            "Python_Entropy",
            "Delta_Python_Entropy",
            
            "Total_Entropy",
            "Delta_Total_Entropy",
            
            "Dependencies_Count",
            
            'SAST_findings_count',
            'SAST_findings_high',
            'SAST_findings_medium',
            'SAST_findings_low',
        ]),
        
        # Salva i dati del commit precedente per calcolare i delta
        previous_code_data = None
        previus_tag = None

        for tag in tags:
        
            commit = tag.commit
            code_data = code_analyzer.code_analyzer_per_commit(commit)
                        
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
                
                code_data.get('total_loc', 0) - (previous_code_data['total_loc'] if previous_code_data else 0),
                code_data.get('total_files', 0) - (previous_code_data['total_files'] if previous_code_data else 0),
                
                code_data.get('function_count', 0),
                code_data.get('function_count', 0) - (previous_code_data['function_count'] if previous_code_data else 0),
                
                code_data.get('async_function_count', 0),
                code_data.get('async_function_count', 0) - (previous_code_data['async_function_count'] if previous_code_data else 0),
                
                code_data.get('class_count', 0),
                code_data.get('class_count', 0) - (previous_code_data['class_count'] if previous_code_data else 0),
                
                code_data.get('python_entropy', 0),
                code_data.get('python_entropy', 0) - (previous_code_data['python_entropy'] if previous_code_data else 0),
                
                code_data.get('total_entropy', 0),
                code_data.get('total_entropy', 0) - (previous_code_data['total_entropy'] if previous_code_data else 0),
                
                code_data.get('dependecies_count', 0),
                
                code_data.get('sast_findings_count', 0),
                code_data.get('sast_findings_high', 0),
                code_data.get('sast_findings_medium', 0),
                code_data.get('sast_findings_low', 0),
                
            ])
            
            code_data_list.append(code_data)
            previous_code_data = code_data
            previus_tag = tag.name
    
    # Estrai i dati per il plotting
    tags_names = [tag.name for tag in tags]

    # Crea il grafico
    plt.figure(figsize=(10, 6))
    plt.plot(tags_names, [data['function_count'] for data in code_data_list], marker='o', linestyle='-', color='b', label='Numero di funzioni')
    plt.plot(tags_names, [data['async_function_count'] for data in code_data_list], marker='o', linestyle='-', color='g', label='Numero di funzioni asincrone')
    plt.plot(tags_names, [data['class_count'] for data in code_data_list], marker='o', linestyle='-', color='r', label='Numero di classi')
    plt.xlabel('Tags')
    plt.ylabel('Numero di funzioni, classi e funzioni asincrone')
    plt.title('Trend delle metriche nel repository')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()  # Aggiungi la legenda
    plt.tight_layout()

    # Mostra il grafico
    #plt.show()
    
    #Salva il grafico in un file
    graph_file_path = os.path.join(base_path, "repo_code_analysis.png")
    
    plt.savefig(graph_file_path)
    print(f"Grafico salvato in {graph_file_path}")
    
    
    
    plt.figure(figsize=(10, 6))
    plt.plot(tags_names, [data['total_loc'] for data in code_data_list], marker='o', linestyle='-', color='b', label='Numero di linee di codice (LoC)')
    plt.xlabel('Tags')
    plt.ylabel('Numero di linee di codice')
    plt.title('Trend delle metriche nel repository')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()  # Aggiungi la legenda
    plt.tight_layout()

    # Mostra il grafico
    #plt.show()
    
    # Salva il grafico in un file
    graph_file_path = os.path.join(base_path, "repo_code_analysis_loc.png")
    
    plt.savefig(graph_file_path)
    print(f"Grafico salvato in {graph_file_path}")
    
    
    
    plt.figure(figsize=(10, 6))
    plt.plot(tags_names, [data['total_files'] for data in code_data_list], marker='o', linestyle='-', color='b', label='Numero di file di codice')
    plt.xlabel('Tags')
    plt.ylabel('Numero di file di codice')
    plt.title('Trend delle metriche nel repository')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()  # Aggiungi la legenda
    plt.tight_layout()

    # Mostra il grafico
    #plt.show()
    
    # Salva il grafico in un file
    graph_file_path = os.path.join(base_path, "repo_code_analysis_files.png")
    
    plt.savefig(graph_file_path)
    print(f"Grafico salvato in {graph_file_path}")


if __name__ == "__main__":
    
    # Scarica il repository se non è già presente
    repo_url = sys.argv[1] if len(sys.argv) > 1 else None
    if not repo_url:
        raise ValueError("Please provide the repository URL as the first argument.")
    
    repo = clone_repo.clone_repo(repo_url)
    repo_name = repo_url.rstrip('/').split('/')[-1].split('.git')[0] 
        
    analyze_repo(repo, repo_name)