import os
import sys
import argparse
import multiprocessing
import pandas as pd
from git import Repo, GitCommandError
from collections import Counter
import time

import unicodedata
import homoglyphs as hg


# Fix relative imports. See https://stackoverflow.com/a/16985066
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from src.utils.clone_repo import clone_repo
from src.utils.log import init_logging, log


# Directory da ignorare durante l'analisi
FILTER_DIRS = [".git", "node_modules", "vendor", "test", "tests", "dist", "build", "public", "assets", "bin", "coverage", "logs"]

# Whitespace characters che non dovrebbero essere considerati sospetti
SAFE_CONTROL_CHARS = {'\n', '\r', '\t', '\f', '\v'}

# Cache per le categorie dei caratteri per evitare calcoli ripetuti
_char_category_cache = {}
_homoglyph_cache = {}

def get_char_categories_cached(char):
    """Cache per le categorie dei caratteri per migliorare le performance"""
    if char not in _char_category_cache:
        try:
            unicode_cat = unicodedata.category(char)
            try:
                homoglyph_cat = hg.Categories.detect(char)
            except:
                homoglyph_cat = 'UNKNOWN'
            _char_category_cache[char] = (unicode_cat, homoglyph_cat)
        except:
            _char_category_cache[char] = ('UNKNOWN', 'UNKNOWN')
    
    return _char_category_cache[char]


def analyze_file_unicode_worker(file_path: str) -> tuple:
    """
    Calcola le statistiche (caratteri totali, omoglifi, nascosti) per un singolo file.
    OTTIMIZZATO: ridotto logging e uso di cache per le categorie.
    """
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            total_chars = len(content)
            homoglyph_count = 0
            hidden_char_count = 0
            
            # Ottimizzazione: conta i caratteri unici invece di analizzare ogni carattere
            char_counts = Counter(content)
            
            suspicious_chars = []  # Per logging ridotto
            
            for char, count in char_counts.items():
                unicode_cat, homoglyph_cat = get_char_categories_cached(char)
                
                # 1. Controllo omoglifi
                if homoglyph_cat not in ('LATIN', 'COMMON', 'UNKNOWN'):
                    homoglyph_count += count
                    suspicious_chars.append(f"Omoglifo '{char}' ({ord(char)}) x{count}")
                        
                # 2. Controllo caratteri nascosti
                if unicode_cat in ('Cf', 'Cc', 'Cn', 'Co') and char not in SAFE_CONTROL_CHARS:
                    hidden_char_count += count
                    suspicious_chars.append(f"Nascosto '{char}' ({ord(char)}) x{count}")
            
            # Logging ridotto: solo un messaggio per file se ci sono caratteri sospetti
            if suspicious_chars:
                log(f"File {file_path}: {', '.join(suspicious_chars[:5])}{'...' if len(suspicious_chars) > 5 else ''}")

            return total_chars, homoglyph_count, hidden_char_count

    except Exception as e:
        log(f"Errore nell'analizzare il file {os.path.basename(file_path)}: {e}", file=sys.stderr)
        return None, None, None


def get_files_for_extension(repo_path: str, extension: str) -> list:
    """
    Raccoglie tutti i file con l'estensione specificata, 
    ottimizzato per evitare ripetizioni.
    """
    files = []
    
    for root, _, filenames in os.walk(repo_path):
        # Skip delle directory filtrate
        if any(filtered_dir in root.replace(repo_path, '').split(os.sep) for filtered_dir in FILTER_DIRS):
            continue
        
        for filename in filenames:
            if filename.endswith(f".{extension}"):
                file_path_abs = os.path.join(root, filename)
                file_path_rel = os.path.relpath(file_path_abs, repo_path)
                files.append((file_path_abs, file_path_rel))
    
    return files


def analyze_repo_unicode_optimized(repo: Repo, extension: str, output_dir: str, num_processes: int = None):
    """
    Versione ottimizzata dell'analisi repository.
    """
    repo_path = repo.working_tree_dir
    repo_name = os.path.basename(repo_path)

    if num_processes is None:
        num_processes = min(multiprocessing.cpu_count(), 8)  # Limita a 8 per evitare overhead
    
    print(f"Utilizzo di {num_processes} processi per l'analisi dei file.")

    # Ordina i tag per data di commit
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
    
    start_time = time.time()

    # Pre-creazione del pool per evitare overhead ripetuti
    with multiprocessing.Pool(processes=num_processes) as pool:
        for idx, tag in enumerate(tags):
            tag_name = tag.name
            tag_start = time.time()
            
            print(f"Analizzando tag: {tag_name} ({idx + 1}/{len(tags)})")
            
            try:
                repo.git.checkout(tag.commit, force=True)
            except GitCommandError as e:
                print(f"Errore durante il checkout del tag {tag_name}: {e}. Salto questo tag.", file=sys.stderr)
                continue

            # Ottimizzazione: raccogli tutti i file una volta sola
            files_data = get_files_for_extension(repo_path, extension)
            
            if not files_data:
                log(f"Nessun file .{extension} trovato nel tag {tag_name}")
                continue
            
            files_absolute = [f[0] for f in files_data]
            files_relative = [f[1] for f in files_data]
            
            # Esegui l'analisi in parallelo
            results = pool.map(analyze_file_unicode_worker, files_absolute)
                        
            # Raccogli i risultati
            tag_total, tag_homoglyphs, tag_hidden = {}, {}, {}
            files_processed = 0
            
            for i, (total, homoglyphs, hidden) in enumerate(results):
                if total is not None:
                    relative_path = files_relative[i]
                    all_files_across_tags.add(relative_path)
                    tag_total[relative_path] = total
                    tag_homoglyphs[relative_path] = homoglyphs
                    tag_hidden[relative_path] = hidden
                    files_processed += 1
            
            total_chars_data[tag_name] = tag_total
            homoglyphs_data[tag_name] = tag_homoglyphs
            hidden_chars_data[tag_name] = tag_hidden
            
            tag_elapsed = time.time() - tag_start
            print(f"  Tag {tag_name} completato in {tag_elapsed:.2f}s - {files_processed} file processati")

    print(f"\nAnalisi completata in {time.time() - start_time:.2f} secondi")
    print("Costruzione dei DataFrame...")

    if not all_files_across_tags:
        log(f"Nessun file con estensione '.{extension}' trovato nei tag analizzati.")
        return
        
    # Resto del codice per la creazione dei DataFrame rimane uguale
    sorted_files_list = sorted(list(all_files_across_tags))
    tag_names_processed = [t.name for t in tags if t.name in total_chars_data]

    df_total = pd.DataFrame(index=sorted_files_list, columns=tag_names_processed)
    df_homoglyphs = pd.DataFrame(index=sorted_files_list, columns=tag_names_processed)
    df_hidden = pd.DataFrame(index=sorted_files_list, columns=tag_names_processed)

    for tag_name in tag_names_processed:
        df_total[tag_name] = pd.Series(total_chars_data.get(tag_name, {})).reindex(df_total.index)
        df_homoglyphs[tag_name] = pd.Series(homoglyphs_data.get(tag_name, {})).reindex(df_homoglyphs.index)
        df_hidden[tag_name] = pd.Series(hidden_chars_data.get(tag_name, {})).reindex(df_hidden.index)

    for df in [df_total, df_homoglyphs, df_hidden]:
        df.fillna('', inplace=True)

    # Salvataggio
    os.makedirs(output_dir, exist_ok=True)
    output_paths = {
        "total_chars": os.path.join(output_dir, f"{repo_name}_total_chars.csv"),
        "homoglyphs": os.path.join(output_dir, f"{repo_name}_homoglyphs.csv"),
        "hidden_chars": os.path.join(output_dir, f"{repo_name}_hidden_chars.csv"),
    }
    
    df_total.to_csv(output_paths["total_chars"])
    df_homoglyphs.to_csv(output_paths["homoglyphs"])
    df_hidden.to_csv(output_paths["hidden_chars"])
    
    elapsed_time = time.time() - start_time
    print(f"\nAnalisi completata con successo in {elapsed_time:.2f} secondi!")
    print("File CSV generati:")
    for key, path in output_paths.items():
        print(f"  - {key}: {path}")


def main():
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
        help="Numero di processi da usare per l'analisi (default: min(CPU, 8))."
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

    # Usa la versione ottimizzata
    analyze_repo_unicode_optimized(repo, args.extension, output_dir, args.num_processes)


if __name__ == "__main__":
    main()