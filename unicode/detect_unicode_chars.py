import os
import sys
import argparse
import multiprocessing
import pandas as pd
from git import Repo, GitCommandError

import unicodedata
import homoglyphs as hg


# Fix relative imports. See https://stackoverflow.com/a/16985066
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from src.utils.clone_repo import clone_repo
from src.utils.log import init_logging, log


# Directory da ignorare durante l'analisi
FILTER_DIRS = [".git", "node_modules", "vendor", "test", "tests"]


def analyze_file_unicode_worker(file_path: str) -> tuple:
    """
    Calcola le statistiche (caratteri totali, omoglifi, nascosti) per un singolo file.
    Ritorna una tupla: (total_chars, homoglyph_count, hidden_char_count)
    """
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            total_chars = len(content)
            homoglyph_count = 0
            hidden_char_count = 0

            for char in content:
                try:
                    # 1. Controllo omoglifi: se il carattere non è latino o comune, conta come omoglifo
                    category = hg.Categories.detect(char)
                    if category != 'LATIN' and category != 'COMMON':
                        log(f"Carattere '{char}' ({ord(char)}) in {file_path} è considerato un omoglifo.")
                        homoglyph_count += 1
                        
                        
                    # 2. Controllo caratteri "nascosti" o di controllo usando unicodedata
                    category = unicodedata.category(char)
                    if category in ('Cf', 'Cc', 'Cn', 'Co'):
                        log(f"Carattere '{char}' ({ord(char)}) in {file_path} è considerato nascosto o di controllo.")
                        hidden_char_count += 1
                except ValueError:
                    # Se unicodedata non riesce a determinare la categoria, ignora l'errore.
                    # Può accadere con caratteri di controllo: https://stackoverflow.com/a/70074874
                    pass

            return total_chars, homoglyph_count, hidden_char_count

    except Exception as e:
        log(f"Errore nell'analizzare il file {file_path}: {e}", file=sys.stderr)
        
        # In caso di errore (es. file binario), ritorna None per ogni metrica
        return None, None, None


def analyze_repo_unicode(repo: Repo, extension: str, output_dir: str, num_processes: int = None):
    """
    Analizza un repository, calcola le statistiche sui caratteri per ogni file
    con l'estensione data per ogni tag, e salva i risultati in file CSV.
    """
    repo_path = repo.working_tree_dir
    repo_name = os.path.basename(repo_path)

    if num_processes is None:
        num_processes = multiprocessing.cpu_count()
    print(f"Utilizzo di {num_processes} processi per l'analisi dei file.")

    # Ordina i tag per data di commit (analisi cronologica)
    try:
        tags = sorted(repo.tags, key=lambda t: t.commit.authored_datetime)
    except Exception as e:
        print(f"Errore nel recuperare o ordinare i tag: {e}", file=sys.stderr)
        return

    if not tags:
        log("Nessun tag trovato nel repository. Analisi interrotta.")
        return

    log(f"Trovati {len(tags)} tag. Inizio analisi per i file con estensione '.{extension}'...")

    all_files_across_tags = set()
    total_chars_data = {}
    homoglyphs_data = {}
    hidden_chars_data = {}
    
    start_time = pd.Timestamp.now()

    with multiprocessing.Pool(processes=num_processes) as pool:
        for idx, tag in enumerate(tags):
            tag_name = tag.name
            log(f"\r\tAnalizzando il tag: {tag_name} ({idx + 1}/{len(tags)})")
            
            try:
                repo.git.checkout(tag.commit, force=True)
            except GitCommandError as e:
                print(f"\nErrore durante il checkout del tag {tag_name}: {e}. Salto questo tag.", file=sys.stderr)
                continue

            files_to_process_absolute = []
            files_to_process_relative = []

            for root, _, files in os.walk(repo_path):
                if any(filtered_dir in root.replace(repo_path, '').split(os.sep) for filtered_dir in FILTER_DIRS):
                    continue
                
                for file_name in files:
                    if file_name.endswith(f".{extension}"):
                        file_path_abs = os.path.join(root, file_name)
                        files_to_process_absolute.append(file_path_abs)
                        files_to_process_relative.append(os.path.relpath(file_path_abs, repo_path))

            # Esegui l'analisi dei file in parallelo
            results = pool.map(analyze_file_unicode_worker, files_to_process_absolute)
                        
            # Raccogli i risultati per il tag corrente
            tag_total, tag_homoglyphs, tag_hidden = {}, {}, {}
            for i, (total, homoglyphs, hidden) in enumerate(results):
                if total is not None:
                    relative_path = files_to_process_relative[i]
                    all_files_across_tags.add(relative_path)
                    tag_total[relative_path] = total
                    tag_homoglyphs[relative_path] = homoglyphs
                    tag_hidden[relative_path] = hidden
            
            total_chars_data[tag_name] = tag_total
            homoglyphs_data[tag_name] = tag_homoglyphs
            hidden_chars_data[tag_name] = tag_hidden

    print("\nAnalisi dei tag completata. Costruzione dei DataFrame...")

    if not all_files_across_tags:
        log(f"Nessun file con estensione '.{extension}' trovato nei tag analizzati. Nessun CSV generato.")
        return
        
    sorted_files_list = sorted(list(all_files_across_tags))
    tag_names_processed = [t.name for t in tags if t.name in total_chars_data]

    # Creazione dei DataFrame
    df_total = pd.DataFrame(index=sorted_files_list, columns=tag_names_processed)
    df_homoglyphs = pd.DataFrame(index=sorted_files_list, columns=tag_names_processed)
    df_hidden = pd.DataFrame(index=sorted_files_list, columns=tag_names_processed)

    # Popolamento dei DataFrame
    for tag_name in tag_names_processed:
        df_total[tag_name] = pd.Series(total_chars_data.get(tag_name, {})).reindex(df_total.index)
        df_homoglyphs[tag_name] = pd.Series(homoglyphs_data.get(tag_name, {})).reindex(df_homoglyphs.index)
        df_hidden[tag_name] = pd.Series(hidden_chars_data.get(tag_name, {})).reindex(df_hidden.index)

    # Gestione dei valori mancanti (file non presenti in un tag)
    for df in [df_total, df_homoglyphs, df_hidden]:
        df.fillna('', inplace=True) # Usa una stringa vuota per i valori mancanti

    # Salvataggio su CSV
    os.makedirs(output_dir, exist_ok=True)
    output_paths = {
        "total_chars": os.path.join(output_dir, f"{repo_name}_total_chars.csv"),
        "homoglyphs": os.path.join(output_dir, f"{repo_name}_homoglyphs.csv"),
        "hidden_chars": os.path.join(output_dir, f"{repo_name}_hidden_chars.csv"),
    }
    
    df_total.to_csv(output_paths["total_chars"])
    df_homoglyphs.to_csv(output_paths["homoglyphs"])
    df_hidden.to_csv(output_paths["hidden_chars"])
    
    elapsed_time = pd.Timestamp.now() - start_time
    log("\nAnalisi completata con successo!")
    log(f"Tempo totale impiegato: {elapsed_time}")
    log("File CSV generati:")
    for key, path in output_paths.items():
        log(f"  - {key}: {path}")


def main():
    # Freeze support è necessario per il multiprocessing su Windows
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(
        description="Analizza un repository Git per caratteri speciali (omoglifi, nascosti) nei file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("repo_url", help="URL del repository Git da analizzare.")
    parser.add_argument("-e", "--extension", required=True, help="Estensione dei file da analizzare (es. 'py', 'js').")
    parser.add_argument(
        "--num-processes", 
        type=int, 
        default=None, 
        help="Numero di processi da usare per l'analisi (default: numero di CPU disponibili)."
    )

    args = parser.parse_args()

    repo = clone_repo(args.repo_url)
    if repo is None:
        sys.exit(1)
    
    repo_name = args.repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    output_dir = os.path.join(os.getcwd(), "analytics", repo_name)
    
    init_logging(
        log_file=os.path.join(output_dir, "unicode_analysis.log"),
        save_file=True,
    )

    analyze_repo_unicode(repo, args.extension, output_dir, args.num_processes)


if __name__ == "__main__":
    main()