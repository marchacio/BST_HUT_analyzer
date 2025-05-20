from git import Repo
import os
import pandas as pd
import sys
from src.utils.clone_repo import clone_repo
import time
import argparse
from src.utils.git_manipulator import perform_local_git_manipulation


filter = [
    ".git",
    "node_modules",  # escludi node_modules per repo JS
    "vendor",       # escludi vendor per repo PHP
    "test",         # escludi test
]


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

def analyze_repo_blank_space_ratio(repo:Repo, repo_path:str, extension:str, output_csv_path="blank_space_ratio.csv"):
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
        print(f"\r\tAnalisi del tag: {tag_name} ({idx+1}/{n_tags})", end='', flush=True)
        
        # Checkout del tag
        repo.git.checkout(tag.commit)
        
        current_files_ratio = {}
        for root, _, files in os.walk(repo_path):
            for file_name in files:
                # Ignora i file contenuti in directory di filtro: filter
                if any(f in root for f in filter):
                    continue
                
                # Filtra per estensione se richiesta
                if extension and not file_name.endswith(f".{extension}"):
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
    
    
def analyze_blank_space_ratio_changes(csv_path, threshold_s=0.5, log_path=None):
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

    file_changes = {}

    for i in range(len(tags) - 1):
        tag_prev = tags[i]
        tag_curr = tags[i+1]

        series_prev = pd.to_numeric(df[tag_prev], errors='coerce')
        series_curr = pd.to_numeric(df[tag_curr], errors='coerce')
        
        diff = (series_curr - series_prev).abs()

        for file_path, difference in diff.items():
            if pd.notna(difference) and difference > threshold_s:
                ratio_prev = series_prev.loc[file_path]
                ratio_curr = series_curr.loc[file_path]
                if pd.notna(ratio_prev) and pd.notna(ratio_curr):
                    if file_path not in file_changes:
                        file_changes[file_path] = {
                            "count": 1,
                            "examples": [(tag_prev, ratio_prev, tag_curr, ratio_curr, difference)]
                        }
                    else:
                        file_changes[file_path]["count"] += 1
                        file_changes[file_path]["examples"].append(
                            (tag_prev, ratio_prev, tag_curr, ratio_curr, difference)
                        )
                        
    def _print(message):
        if log_path:
            with open(log_path, 'a') as log_file:
                log_file.write(message + '\n')
        
        print(message)

    if not file_changes:
        _print(f"Nessun cambiamento significativo nel rapporto spazi bianchi è stato trovato sopra la soglia di {threshold_s}.")
    else:
        for file_path, info in file_changes.items():
            _print(f"--FILE: {file_path} (trovato {info['count']} volte)")
            # Mostra solo il primo esempio per brevità, oppure tutti se preferisci
            for tag_prev, ratio_prev, tag_curr, ratio_curr, difference in info["examples"]:
                _print(f"  Tag precedente ({tag_prev}): {ratio_prev:.4f}")
                _print(f"  Tag corrente ({tag_curr}): {ratio_curr:.4f}")
                _print(f"  Differenza assoluta: {difference:.4f} (Supera soglia {threshold_s})")
                _print('\n')
            _print("-" * 50)

    _print(f"Analisi completata. {sum(info['count'] for info in file_changes.values())} cambiamenti significativi trovati.")

# --- Esempio di utilizzo ---
if __name__ == "__main__":
    
    # Parser per argomenti da linea di comando
    parser = argparse.ArgumentParser(description="Analizza il rapporto spazi bianchi nei file di un repository.")
    parser.add_argument("repo_url", help="URL del repository da analizzare")
    parser.add_argument("-e", "--extension", default=None, help="Estensione dei file da analizzare (es: py, js, txt). Se non specificata, analizza tutti i file di testo.")
    args = parser.parse_args()

    repo_url = args.repo_url
    repo_name = repo_url.rstrip('/').split('/')[-1]
    repo_name = repo_name.split('.git')[0]  # Rimuovi .git se presente

    repo = clone_repo(repo_url)
    repo_path = repo.working_tree_dir
    
    # Esegui la manipolazione locale del repository (se necessario)
    edited_file = perform_local_git_manipulation(repo_path, 
        file_extension=args.extension,
        filters=filter
    )

    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(current_dir)

    output_dir = os.path.join(current_dir, "analytics", repo_name)
    os.makedirs(output_dir, exist_ok=True)
    output_csv = os.path.join(output_dir, f"{repo_name}_blank_space_ratio_report.csv")
    print(f"Output CSV: {output_csv}")
    output_log = os.path.join(output_dir, f"{repo_name}_blank_space_ratio_report.log")
    print(f"Output Log: {output_log}")

    analyze_repo_blank_space_ratio(repo, repo_path, args.extension, output_csv)
    
    analyze_blank_space_ratio_changes(output_csv, 2, output_log)