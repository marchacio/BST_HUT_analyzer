from git import Repo
import os
import pandas as pd
import sys
from src.utils.clone_repo import clone_repo
import time

def calculate_blank_space_ratio(file_path):
    """
    Calcola il blank_space_ratio per un dato file.
    blank_space_ratio = numero_totale_caratteri / numero_spazi_bianchi
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            all_chars = len(content)
            blank_spaces = content.count(' ') + content.count('\t') + content.count('\n') + content.count('\r')
            
            if blank_spaces == 0:
                return float('inf')  # Per evitare divisione per zero, se non ci sono spazi bianchi
            else:
                return all_chars / blank_spaces
    except Exception as e:
        print(f"Errore durante l'analisi del file {file_path}: {e}")
        return None

def analyze_repo_blank_space_ratio(repo:Repo, repo_path:str, output_csv_path="blank_space_ratio.csv"):
    """
    Analizza un repository Git per ogni tag, calcolando il blank_space_ratio per ogni file.
    I risultati vengono salvati in un CSV.
    """

    tags = sorted(repo.tags, key=lambda t: t.commit.authored_datetime)
    all_files_across_tags = set()
    data = {}

    n_tags = len(tags)
    print(f"Trovati {n_tags} tag nel repository.")
    
    start_time = time.time()

    for idx, tag in enumerate(tags):
        tag_name = tag.name
        print(f"Analisi del tag: {tag_name} ({idx}/{n_tags})", end=' ')
        
        # Checkout del tag
        repo.git.checkout(tag.commit)
        
        current_files_ratio = {}
        for root, _, files in os.walk(repo_path):
            for file_name in files:
                # Ignora la directory .git e file binari comuni
                if '.git' in root or ('node_modules' in file_name) or file_name.endswith(('.pyc', '.o', '.so', '.dll', '.exe', '.zip', '.tar.gz', '.jpg', '.png', '.gif', '.bmp', '.pdf')):
                    continue
                
                file_path = os.path.join(root, file_name)
                # Assicurati che il percorso sia relativo al root del repository per l'identificazione nel CSV
                relative_file_path = os.path.relpath(file_path, repo_path)
                
                ratio = calculate_blank_space_ratio(file_path)
                if ratio is not None:
                    current_files_ratio[relative_file_path] = ratio
                    all_files_across_tags.add(relative_file_path)
        
        data[tag_name] = current_files_ratio

    # Costruisci il DataFrame
    df = pd.DataFrame(index=sorted(list(all_files_across_tags)))

    for tag_name in [t.name for t in tags]:
        tag_data = data.get(tag_name, {})
        column_values = [tag_data.get(file_path, '') for file_path in df.index]
        df[tag_name] = column_values

    # Reset del repository allo stato originale (ad esempio, al branch master/main)
    try:
        current_branch = repo.active_branch.name
        repo.git.checkout(current_branch)
        print(f"Ripristinato il repository al branch: {current_branch}")
    except Exception as e:
        print(f"Attenzione: Impossibile ripristinare il repository al branch originale. Potrebbe essere in stato di 'detached HEAD'. Errore: {e}")
        print("Si prega di ripristinare manualmente il branch desiderato (es. 'git checkout master').")

    # Salva il DataFrame in un CSV
    df.to_csv(output_csv_path)
    print(f"Analisi completata. I risultati sono stati salvati in '{output_csv_path}'")

    elapsed_time = time.time() - start_time
    print(f"Tempo impiegato per l'analisi: {elapsed_time:.2f} secondi")
    
    
import pandas as pd

def analyze_blank_space_ratio_changes(csv_path, threshold_s=0.5):
    """
    Analizza un CSV di blank_space_ratio per identificare cambiamenti significativi.

    Args:
        csv_path (str): Il percorso al file CSV generato dallo script precedente.
        threshold_s (float): La soglia minima per la differenza assoluta
                             tra i rapporti di due tag consecutivi per essere considerata significativa.
    """
    try:
        df = pd.read_csv(csv_path, index_col=0)
    except FileNotFoundError:
        print(f"Errore: Il file CSV non trovato a '{csv_path}'. Assicurati che il percorso sia corretto.")
        return
    except Exception as e:
        print(f"Errore durante la lettura del file CSV: {e}")
        return

    tags = df.columns.tolist()
    
    if len(tags) < 2:
        print("Il CSV contiene meno di due tag. Non è possibile calcolare le differenze tra tag successivi.")
        return

    print(f"Analisi delle differenze nel rapporto spazi bianchi con soglia S = {threshold_s}\n")

    found_significant_changes = False

    for i in range(len(tags) - 1):
        tag_prev = tags[i]
        tag_curr = tags[i+1]

        # Considera solo i valori numerici e gestisci i valori mancanti come NaN
        # Converti i valori vuoti o non numerici in NaN, poi fillna(method='ffill') o fillna(0) se necessario
        # Per questo caso specifico, vogliamo NaN per indicare che il file non esiste ancora o è stato rimosso
        series_prev = pd.to_numeric(df[tag_prev], errors='coerce')
        series_curr = pd.to_numeric(df[tag_curr], errors='coerce')
        
        diff = (series_curr - series_prev).abs()

        # Itera sui file per trovare le differenze significative
        for file_path, difference in diff.items():
            # Controlla se il file esisteva in entrambi i tag e la differenza è significativa
            if pd.notna(difference) and difference > threshold_s:
                ratio_prev = series_prev.loc[file_path]
                ratio_curr = series_curr.loc[file_path]

                # Filtra ulteriormente per assicurarsi che i valori originali non siano NaN
                if pd.notna(ratio_prev) and pd.notna(ratio_curr):
                    print(f"File: {file_path}")
                    print(f"  Tag precedente ({tag_prev}): {ratio_prev:.4f}")
                    print(f"  Tag corrente ({tag_curr}): {ratio_curr:.4f}")
                    print(f"  Differenza assoluta: {difference:.4f} (Supera soglia {threshold_s})")
                    print("-" * 50)
                    found_significant_changes = True

    if not found_significant_changes:
        print(f"Nessun cambiamento significativo nel rapporto spazi bianchi è stato trovato sopra la soglia di {threshold_s}.")

# --- Esempio di utilizzo ---
if __name__ == "__main__":
    
    # scarica il repo passato come primo argomento
    repo_url = sys.argv[1] if len(sys.argv) > 1 else ""
    repo_name = repo_url.rstrip('/').split('/')[-1]
    repo_name = repo_name.split('.git')[0]  # Rimuovi .git se presente
    
    repo = clone_repo(repo_url)
    repo_path = repo.working_tree_dir
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(current_dir)
    output_csv = os.path.join(current_dir, "analytics", repo_name, "blank_space_ratio_report.csv",)
    print(f"Output CSV: {output_csv}")
    
    analyze_repo_blank_space_ratio(repo, repo_path, output_csv)
    
    analyze_blank_space_ratio_changes(output_csv, 2)