from git import Repo
import os
import pandas as pd
import sys
import time
import argparse
import multiprocessing # Importa multiprocessing
from functools import partial # Utile per passare argomenti fissi a map
from src.utils.clone_repo import clone_repo
from src.utils.git_manipulator import perform_local_git_manipulation

filter_dirs = [ # Rinominato per chiarezza, questi sono nomi di directory
    ".git",
    "node_modules",
    "vendor",
    "test",
]

def calculate_blank_space_ratio_worker(file_path): # Nome leggermente modificato per chiarezza
    """
    Calcola il blank_space_ratio per un dato file e la lunghezza della riga più lunga.
    blank_space_ratio = numero_totale_caratteri / numero_spazi_bianchi
    Ritorna una tupla: (blank_space_ratio, max_line_length)
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            all_chars = len(content)
            blank_spaces = content.count(' ') + content.count('\t') + content.count('\n') + content.count('\r')
            
            lines = content.splitlines()
            max_line_length = max((len(line) for line in lines), default=0)
            if blank_spaces == 0:
                ratio = float('inf') # O potresti decidere di ritornare 0 o None se preferisci
            else:
                ratio = all_chars / blank_spaces
                
            return ratio, max_line_length
    except Exception: # Evita di stampare qui, gestisci il None nel chiamante
        # print(f"Errore durante l'analisi del file {file_path}: {e}") # Rimosso per output più pulito in parallelo
        return None, None

def analyze_repo_blank_space_ratio(repo:Repo, repo_path:str, extension:str, 
        ratio_output_csv_path="blank_space_ratio.csv",
        max_line_length_output_csv_path="max_line_length.csv",
        num_processes=None # Aggiunto parametro per il numero di processi
    ):
    """
    Analizza un repository Git per ogni tag, calcolando il blank_space_ratio e max_line_length per ogni file.
    I risultati vengono salvati in due CSV, uno per ogni ricerca.
    """
    if num_processes is None:
        num_processes = multiprocessing.cpu_count()
    print(f"Utilizzo di {num_processes} processi per l'analisi dei file.")

    tags = sorted(repo.tags, key=lambda t: t.commit.authored_datetime)
    all_files_across_tags = set()
    ratio_data = {}
    max_line_length_data = {}

    n_tags = len(tags)
    if n_tags == 0:
        print("Nessun tag trovato nel repository. Analisi interrotta.")
        # Prova ad analizzare il commit corrente se non ci sono tag
        # Potresti voler gestire il caso in cui non ci sono tag,
        # ad esempio analizzando il commit HEAD corrente.
        # Per ora, usciamo se non ci sono tag.
        # Se vuoi analizzare HEAD, dovrai modificare la logica per gestire un "tag fittizio" o il commit corrente.
        # head_commit = repo.head.commit
        # tags = [type('obj', (object,), {'name': 'HEAD', 'commit': head_commit })] # Oggetto fittizio simile a un tag
        # n_tags = 1
        # print("Nessun tag trovato. Analizzo HEAD.")
        # if not tags: # Assicurati che ci sia qualcosa da analizzare
        print("Nessun tag trovato. Analisi interrotta.")
        # Crea DataFrame vuoti se non ci sono tag per evitare errori successivi
        pd.DataFrame().to_csv(ratio_output_csv_path)
        pd.DataFrame().to_csv(max_line_length_output_csv_path)
        print(f"File CSV vuoti creati: '{ratio_output_csv_path}' e '{max_line_length_output_csv_path}'.")
        return


    print(f"Trovati {n_tags} tag nel repository.")
    
    start_time = time.time()

    # Crea il pool di processi una volta, fuori dal loop dei tag
    with multiprocessing.Pool(processes=num_processes) as pool:
        for idx, tag in enumerate(tags):
            tag_name = tag.name
            print(f"\r\tAnalisi del tag: {tag_name} ({idx+1}/{n_tags})", end='', flush=True)
            
            try:
                repo.git.checkout(tag.commit, force=True) # Aggiunto force=True per gestire meglio cambi tra tag
            except Exception as e:
                print(f"\nErrore durante il checkout del tag {tag_name}: {e}. Salto questo tag.")
                continue

            files_to_process_absolute = []
            files_to_process_relative = []

            for root, _, files in os.walk(repo_path):
                # Ignora i file contenuti in directory di filtro: filter_dirs
                if any(filtered_dir in root.replace(repo_path, '').split(os.sep) for filtered_dir in filter_dirs):
                    continue
                
                for file_name in files:
                    if extension and not file_name.endswith(f".{extension}"):
                        continue
                    
                    file_path_absolute = os.path.join(root, file_name)
                    file_path_relative = os.path.relpath(file_path_absolute, repo_path)
                    
                    files_to_process_absolute.append(file_path_absolute)
                    files_to_process_relative.append(file_path_relative)

            # Esegui l'analisi dei file in parallelo
            # calculate_blank_space_ratio_worker prende solo file_path_absolute
            results = pool.map(calculate_blank_space_ratio_worker, files_to_process_absolute)
            
            current_files_ratio = {}
            current_files_max_line_length = {}

            for i, (ratio, max_len) in enumerate(results):
                relative_path = files_to_process_relative[i]
                if ratio is not None and max_len is not None:
                    current_files_ratio[relative_path] = ratio
                    current_files_max_line_length[relative_path] = max_len
                    all_files_across_tags.add(relative_path)
            
            ratio_data[tag_name] = current_files_ratio
            max_line_length_data[tag_name] = current_files_max_line_length

    print("\nCostruzione dei DataFrame...")
    # Costruisci il DataFrame
    # Assicurati che all_files_across_tags non sia vuoto per evitare errori con pd.DataFrame
    if not all_files_across_tags:
        print("Nessun file analizzato su tutti i tag. I CSV saranno vuoti.")
        sorted_files_list = []
    else:
        sorted_files_list = sorted(list(all_files_across_tags))

    ratio_df = pd.DataFrame(index=sorted_files_list)
    max_line_length_df = pd.DataFrame(index=sorted_files_list)

    tag_names_processed = [t.name for t in tags if t.name in ratio_data] # Usa solo tag effettivamente processati

    for tag_name in tag_names_processed:
        ratio_tag_data = ratio_data.get(tag_name, {})
        max_line_length_tag_data = max_line_length_data.get(tag_name, {})
        
        # Usa reindex per assicurare che tutti i file siano presenti e nell'ordine corretto, riempiendo con '' o NaN
        ratio_df[tag_name] = pd.Series(ratio_tag_data).reindex(ratio_df.index).fillna('')
        max_line_length_df[f"{tag_name}_max_line_length"] = pd.Series(max_line_length_tag_data).reindex(max_line_length_df.index).fillna('')


    # Reset del repository allo stato originale
    try:
        # Cerca il branch di default comune (main o master)
        default_branch = None
        if 'main' in repo.heads:
            default_branch = 'main'
        elif 'master' in repo.heads:
            default_branch = 'master'
        
        if default_branch:
            print(f"\nTentativo di ripristino al branch: {default_branch}")
            repo.git.checkout(default_branch)
            print(f"Repository ripristinato al branch: {default_branch}")
        elif repo.active_branch: # Se non trova main/master, prova il branch attivo all'inizio (se c'era)
             current_branch_name = repo.active_branch.name # Questo potrebbe dare errore se in detached HEAD all'inizio
             repo.git.checkout(current_branch_name)
             print(f"\nRipristinato il repository al branch: {current_branch_name}")
        else: # Fallback se non si può determinare un branch
            print(f"\nAttenzione: Impossibile determinare un branch di default (main/master) per il ripristino.")
            print("Il repository potrebbe essere in stato 'detached HEAD'.")
            print("Si prega di ripristinare manualmente il branch desiderato (es. 'git checkout main').")

    except Exception as e:
        print(f"\nAttenzione: Impossibile ripristinare il repository a un branch. Potrebbe essere in stato 'detached HEAD'. Errore: {e}")
        print("Si prega di ripristinare manualmente il branch desiderato (es. 'git checkout main').")


    # Salva il DataFrame in un CSV
    ratio_df.to_csv(ratio_output_csv_path)
    max_line_length_df.to_csv(max_line_length_output_csv_path)
    print(f"Analisi completata. I risultati sono stati salvati in '{ratio_output_csv_path}' e '{max_line_length_output_csv_path}'.")

    elapsed_time = time.time() - start_time
    print(f"Tempo impiegato per l'analisi: {elapsed_time:.2f} secondi")
    
    
def analyze_blank_space_ratio_changes(csv_path, threshold_mean=0.5, threshold_previous=0.5, log_path=None):
    """
    Analizza un CSV di blank_space_ratio per identificare cambiamenti significativi
    rispetto alla media dei tag precedenti E rispetto al tag precedente.

    Args:
        csv_path (str): Il percorso al file CSV generato dallo script precedente.
        threshold_mean (float): La soglia minima per la deviazione assoluta
                                dal rapporto medio dei tag precedenti.
        threshold_previous (float): La soglia minima per la differenza assoluta
                                    tra il rapporto corrente e il rapporto del tag precedente.
        log_path (str, optional): Il percorso del file di log.
    """
    try:
        # Specifica il tipo di dati per evitare il warning e assicurare che i valori vuoti siano NaN
        df = pd.read_csv(csv_path, index_col=0, na_values=[''])
    except FileNotFoundError:
        print(f"Errore: Il file CSV non trovato a '{csv_path}'. Assicurati che il percorso sia corretto.")
        return
    except Exception as e:
        print(f"Errore durante la lettura del file CSV: {e}")
        return

    # Se il dataframe è vuoto (nessun file analizzato o nessun tag)
    if df.empty or len(df.columns) == 0:
        print("Il CSV è vuoto o non contiene dati di tag. Analisi delle deviazioni saltata.")
        if log_path:
            with open(log_path, 'w') as log_file: # Crea o sovrascrivi il file di log
                log_file.write("Il CSV di input era vuoto. Nessuna analisi delle deviazioni eseguita.\n")
        return

    tags = df.columns.tolist()
    
    if len(tags) < 2:
        message = "Il CSV contiene meno di due tag. Non è possibile calcolare le differenze."
        print(message)
        if log_path:
            with open(log_path, 'w') as log_file: # Crea o sovrascrivi il file di log
                log_file.write(message + "\n")
        return

    print(f"Analisi delle deviazioni (media e precedente) con soglie: Media={threshold_mean}, Precedente={threshold_previous}\n")

    file_deviations = {}

    # Cancella o crea il file di log
    if log_path:
        with open(log_path, 'w') as log_file: # 'w' per sovrascrivere/creare
            log_file.write(f"Inizio analisi deviazioni con soglie: Media={threshold_mean}, Precedente={threshold_previous}\n\n")


    def _print(message):
        if log_path:
            with open(log_path, 'a') as log_file:
                log_file.write(message + '\n')
        print(message)
    
    for file_path in df.index:
        # Estrai i rapporti per il file corrente, converti in numerico e gestisci NaN
        # pd.to_numeric convertirà correttamente le stringhe vuote (da .fillna('')) in NaN se 'coerce' è usato
        ratios = pd.to_numeric(df.loc[file_path], errors='coerce')
        
        for i in range(1, len(tags)):
            tag_curr_name = tags[i]
            tag_prev_name = tags[i-1]
            
            ratio_curr = ratios.loc[tag_curr_name]

            if pd.isna(ratio_curr):
                continue 

            ratio_prev = float('nan')
            mean_prev_ratios = float('nan')
            deviation_from_previous = float('inf') 
            deviation_from_mean = float('inf') 

            if pd.notna(ratios.loc[tag_prev_name]):
                ratio_prev = ratios.loc[tag_prev_name]
                if pd.notna(ratio_prev): # Assicurati che ratio_prev sia numerico
                    deviation_from_previous = abs(ratio_curr - ratio_prev)
            
            previous_tags_for_mean_ratios = ratios.iloc[:i].dropna()

            if not previous_tags_for_mean_ratios.empty: # Modificato per controllare se la Series non è vuota
                mean_prev_ratios = previous_tags_for_mean_ratios.mean()
                if pd.notna(mean_prev_ratios): # Assicurati che la media sia numerica
                    deviation_from_mean = abs(ratio_curr - mean_prev_ratios)

            if (deviation_from_previous != float('inf') and deviation_from_previous > threshold_previous and
                deviation_from_mean != float('inf') and deviation_from_mean > threshold_mean):

                if file_path not in file_deviations:
                    file_deviations[file_path] = []
                
                file_deviations[file_path].append({
                    "tag_current": tag_curr_name,
                    "tag_previous": tag_prev_name, 
                    "ratio_current": ratio_curr,
                    "ratio_previous": ratio_prev,
                    "mean_previous_ratios": mean_prev_ratios,
                    "deviation_from_previous": deviation_from_previous,
                    "deviation_from_mean": deviation_from_mean
                })
                        
    total_deviations_found = 0 # Inizializza qui
    if not file_deviations:
        _print(f"Nessun cambiamento significativo (rispetto alla media E al precedente) è stato trovato sopra le soglie: Media={threshold_mean}, Precedente={threshold_previous}.")
    else:
        _print(f"Trovate {len(file_deviations)} file con cambiamenti significativi (rispetto alla media E al precedente) sopra le soglie: Media={threshold_mean}, Precedente={threshold_previous}.\n")
        
        calculate_max_line_length = False
        max_line_length_df = None # Inizializza a None
        try:
            # Costruisci il nome del file max_line_length basandoti sul nome del file ratio
            # Questo è più robusto che fare replace su una stringa fissa
            base_csv_name = os.path.basename(csv_path)
            if "_blank_space_ratio_report.csv" in base_csv_name:
                max_line_length_csv_name = base_csv_name.replace("_blank_space_ratio_report.csv", "_max_line_length_report.csv")
            else: # Fallback se il nome non corrisponde al pattern atteso
                max_line_length_csv_name = "max_line_length_report.csv" 
            
            max_line_length_csv_full_path = os.path.join(os.path.dirname(csv_path), max_line_length_csv_name)
            
            _print(f"Tentativo di leggere il file max_line_length da: {max_line_length_csv_full_path}")

            max_line_length_df = pd.read_csv(max_line_length_csv_full_path, index_col=0, na_values=[''])
            
            if max_line_length_df.empty and not df.empty : # Se il df principale non è vuoto ma questo sì
                 _print(f"Attenzione: Il file {max_line_length_csv_full_path} è vuoto.")
                 # Non impostare calculate_max_line_length = False, così tenterà comunque di accedere
                 # e gestirà l'assenza di colonne/indici con "N/A"
            
            calculate_max_line_length = True # Imposta a True se il file è letto, anche se vuoto
        except FileNotFoundError:
            _print(f"Avviso: File {max_line_length_csv_full_path} non trovato. Le informazioni sulla lunghezza massima della riga non saranno incluse.")
        except Exception as e:
            _print(f"Errore durante la lettura del file {max_line_length_csv_full_path}: {e}. Le informazioni sulla lunghezza massima della riga non saranno incluse.")
        
        for file_path, deviations_list in file_deviations.items():
            _print(f"--FILE: {file_path}\n")
            for dev_info in deviations_list:
                prev_tag = dev_info['tag_previous']
                curr_tag = dev_info['tag_current']
                prev_ratio_val = dev_info['ratio_previous']
                curr_ratio_val = dev_info['ratio_current']

                prev_ratio_str = f"{prev_ratio_val:.4f}" if pd.notna(prev_ratio_val) else "N/A"
                curr_ratio_str = f"{curr_ratio_val:.4f}" if pd.notna(curr_ratio_val) else "N/A"
                
                diff_ratio_str = "N/A"
                if pd.notna(dev_info['deviation_from_previous']):
                     diff_ratio_str = f"{dev_info['deviation_from_previous']:.4f}"


                max_length_prev_val = "N/A"
                max_length_curr_val = "N/A"
                diff_max_len_str = "N/A"

                if calculate_max_line_length and max_line_length_df is not None and file_path in max_line_length_df.index:
                    prev_col_name = f"{prev_tag}_max_line_length"
                    curr_col_name = f"{curr_tag}_max_line_length"
                    
                    if prev_col_name in max_line_length_df.columns:
                        val = max_line_length_df.loc[file_path, prev_col_name]
                        max_length_prev_val = int(val) if pd.notna(val) and val != '' else "N/A"
                    
                    if curr_col_name in max_line_length_df.columns:
                        val = max_line_length_df.loc[file_path, curr_col_name]
                        max_length_curr_val = int(val) if pd.notna(val) and val != '' else "N/A"

                    if isinstance(max_length_curr_val, int) and isinstance(max_length_prev_val, int):
                        diff_max_len_str = f"{abs(max_length_curr_val - max_length_prev_val)}"


                _print(f"{'':<28}|{prev_tag:<20}|{curr_tag:<20}|{'DIFFERENCE (ABS)':<20}")
                _print(f"{'-'*28}|{'-'*20}|{'-'*20}|{'-'*20}")
                _print(f"{'Blank space ratio':<28}|{prev_ratio_str:<20}|{curr_ratio_str:<20}|{diff_ratio_str:<20}")
                _print(f"{'Max line length':<28}|{str(max_length_prev_val):<20}|{str(max_length_curr_val):<20}|{diff_max_len_str:<20}")
                _print("")                        
                total_deviations_found += 1
            _print("#" * 80 + "\n")

    _print(f"Analisi completata. {total_deviations_found} deviazioni significative trovate.")

# --- Esempio di utilizzo ---
if __name__ == "__main__":
    # Necessario per multiprocessing su Windows
    multiprocessing.freeze_support() # Aggiungi questo per compatibilità Windows

    parser = argparse.ArgumentParser(description="Analizza il rapporto spazi bianchi nei file di un repository.")
    parser.add_argument("repo_url", help="URL del repository da analizzare")
    parser.add_argument("-e", "--extension", default=None, help="Estensione dei file da analizzare (es: py, js, txt). Se non specificata, analizza tutti i file.")
    parser.add_argument("-sm", "--threshold_mean", type=float, default=1.0, 
                        help="Soglia di deviazione per la media dei rapporti precedenti. Default è 1.0.")
    parser.add_argument("-sp", "--threshold_previous", type=float, default=1.0, 
                        help="Soglia di deviazione per il rapporto del tag precedente. Default è 1.0.")
    parser.add_argument("-n", "--num-empty-chars", type=int, default=600, help="Numero di caratteri vuoti da aggiungere prima della vulnerabilità. Default 600.")
    parser.add_argument("--num-processes", type=int, default=None, help="Numero di processi da usare per l'analisi dei file (default: numero di CPU).")

    args = parser.parse_args()

    repo_url = args.repo_url
    repo_name = repo_url.rstrip('/').split('/')[-1]
    repo_name = repo_name.split('.git')[0]

    # Clona il repository o ottieni l'oggetto Repo se già clonato
    repo = clone_repo(repo_url)
    if repo is None:
        print(f"Impossibile clonare o accedere al repository: {repo_url}")
        sys.exit(1)
    repo_path = repo.working_tree_dir
    
    print(f"Repository path: {repo_path}")

    # Esegui la manipolazione locale del repository
    # NOTA: perform_local_git_manipulation ora usa 'filter_dirs'
    edited_file_path = perform_local_git_manipulation(
        repo_path, 
        file_extension=args.extension if args.extension else ".py", # Passa .py se nessuna estensione è data per la manipolazione
        filters=filter_dirs, # Usa la variabile globale filter_dirs
        n_blank_chars=args.num_empty_chars
    )

    # current_dir = os.path.dirname(os.path.abspath(__file__)) # Questo potrebbe non essere affidabile se lo script è impacchettato
    current_dir = os.getcwd() # Usa la directory di lavoro corrente per l'output
    print(f"Current working directory for output: {current_dir}")

    output_dir = os.path.join(current_dir, "analytics", repo_name)
    os.makedirs(output_dir, exist_ok=True)
    
    output_max_line_length_csv = os.path.join(output_dir, f"{repo_name}_max_line_length_report.csv")
    output_ratio_csv = os.path.join(output_dir, f"{repo_name}_blank_space_ratio_report.csv")
    output_log = os.path.join(output_dir, f"{repo_name}_deviation_report.log") # Nome più descrittivo per il log
    
    print(f"Output Max Line Length CSV: {output_max_line_length_csv}")
    print(f"Output Blank Space Ratio CSV: {output_ratio_csv}")
    print(f"Output Deviation Log: {output_log}")
    
    # Analizza il repository
    analyze_repo_blank_space_ratio(
        repo, 
        repo_path, 
        args.extension, 
        output_ratio_csv, 
        output_max_line_length_csv,
        num_processes=args.num_processes # Passa il numero di processi
    )
    
    analyze_blank_space_ratio_changes(
        output_ratio_csv, 
        args.threshold_mean, 
        args.threshold_previous, 
        output_log
    )
    
    if edited_file_path and os.path.exists(edited_file_path):
        edited_file_last_line_n = 0
        try:
            with open(edited_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                edited_file_last_line_n = len(lines)
            print(f"Il file a cui è stata aggiunta una \"backdoor\": {edited_file_path}:{edited_file_last_line_n}")
        except Exception as e:
            print(f"Errore leggendo il file modificato {edited_file_path}: {e}")
    elif edited_file_path is None and args.num_empty_chars > 0 : # Se la manipolazione era attesa ma non è avvenuta
        print("La manipolazione del file per aggiungere la backdoor sembra non essere riuscita o nessun file target è stato trovato.")
    else: # Se num_empty_chars era 0, la manipolazione potrebbe non aver fatto nulla intenzionalmente
        print("Nessuna manipolazione del file eseguita o il file modificato non è stato trovato.")