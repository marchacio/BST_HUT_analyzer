from git import Repo
import os
import pandas as pd
import sys
# Assumendo che queste importazioni siano correttamente configurate nel tuo ambiente
from src.utils.clone_repo import clone_repo
from src.utils.git_manipulator import perform_local_git_manipulation
import time
import argparse


filter = [
    ".git",
    "node_modules",  # escludi node_modules per repo JS
    "vendor",       # escludi vendor per repo PHP
    "test",         # escludi test
]


def calculate_blank_space_ratio(file_path):
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
                ratio = float('inf')
            else:
                ratio = all_chars / blank_spaces
                
            return ratio, max_line_length
    except Exception as e:
        print(f"Errore durante l'analisi del file {file_path}: {e}")
        return None, None

def analyze_repo_blank_space_ratio(repo:Repo, repo_path:str, extension:str, 
        ratio_output_csv_path="blank_space_ratio.csv",
        max_line_length_output_csv_path="max_line_length.csv",    
    ):
    """
    Analizza un repository Git per ogni tag, calcolando il blank_space_ratio e max_line_length per ogni file.
    I risultati vengono salvati in due CSV, uno per ogni ricerca.
    """

    tags = sorted(repo.tags, key=lambda t: t.commit.authored_datetime)
    all_files_across_tags = set()
    ratio_data = {}
    max_line_length_data = {}

    n_tags = len(tags)
    print(f"Trovati {n_tags} tag nel repository.")
    
    start_time = time.time()

    for idx, tag in enumerate(tags):
        tag_name = tag.name
        print(f"\r\tAnalisi del tag: {tag_name} ({idx+1}/{n_tags})", end='', flush=True)
        
        # Checkout del tag
        repo.git.checkout(tag.commit)
        
        current_files_ratio = {}
        current_files_max_line_length = {}
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
                
                # Ottieni i rapporti di spazio vuoto e lunghezza della riga
                # più lunga per il file corrente e salvali (se non nulli)
                ratio, max_line_length = calculate_blank_space_ratio(file_path)
                
                if ratio is not None and max_line_length is not None:
                    current_files_ratio[relative_file_path] = ratio
                    current_files_max_line_length[relative_file_path] = max_line_length
                    all_files_across_tags.add(relative_file_path)
        
        ratio_data[tag_name] = current_files_ratio
        max_line_length_data[tag_name] = current_files_max_line_length

    # Costruisci il DataFrame
    ratio_df = pd.DataFrame(index=sorted(list(all_files_across_tags)))
    max_line_length_df = pd.DataFrame(index=sorted(list(all_files_across_tags)))

    for tag_name in [t.name for t in tags]:
        ratio_tag_data = ratio_data.get(tag_name, {})
        max_line_length_tag_data = max_line_length_data.get(tag_name, {})
        
        ratio_column_values = [ratio_tag_data.get(file_path, '') for file_path in ratio_df.index]
        max_line_length_column_values = [max_line_length_tag_data.get(file_path, '') for file_path in ratio_df.index]
        
        # Aggiungi la colonna per il tag corrente
        ratio_df[tag_name] = ratio_column_values
        max_line_length_df[f"{tag_name}_max_line_length"] = max_line_length_column_values

    # Reset del repository allo stato originale (ad esempio, al branch master/main)
    try:
        current_branch = repo.active_branch.name
        repo.git.checkout(current_branch)
        print(f"\nRipristinato il repository al branch: {current_branch}")
    except Exception as e:
        print(f"\nAttenzione: Impossibile ripristinare il repository al branch originale. Potrebbe essere in stato di 'detached HEAD'. Errore: {e}")
        print("Si prega di ripristinare manualmente il branch desiderato (es. 'git checkout master').")

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
        df = pd.read_csv(csv_path, index_col=0)
    except FileNotFoundError:
        print(f"Errore: Il file CSV non trovato a '{csv_path}'. Assicurati che il percorso sia corretto.")
        return
    except Exception as e:
        print(f"Errore durante la lettura del file CSV: {e}")
        return

    tags = df.columns.tolist()
    
    if len(tags) < 2:
        print("Il CSV contiene meno di due tag. Non è possibile calcolare le differenze.")
        return

    print(f"Analisi delle deviazioni (media e precedente) con soglie: Media={threshold_mean}, Precedente={threshold_previous}\n")

    file_deviations = {}

    def _print(message):
        if log_path:
            with open(log_path, 'a') as log_file:
                log_file.write(message + '\n')
        
        print(message)
    
    # Cancella il file di log se esiste
    if log_path and os.path.exists(log_path):
        os.remove(log_path)

    for file_path in df.index:
        
        # Estrai i rapporti per il file corrente, converti in numerico e gestisci NaN
        ratios = pd.to_numeric(df.loc[file_path], errors='coerce')
        
        # Iteriamo sui tag partendo dal secondo tag (indice 1), poiché abbiamo bisogno di un tag precedente
        for i in range(1, len(tags)):
            tag_curr_name = tags[i]
            tag_prev_name = tags[i-1] # Il tag immediatamente precedente
            
            ratio_curr = ratios.loc[tag_curr_name] # Il rapporto corrente per questo tag

            # Se il rapporto corrente non esiste o è NaN, saltiamo
            if pd.isna(ratio_curr):
                continue 

            # Inizializza le variabili con valori di default che non soddisferanno la condizione
            # se i calcoli non sono possibili.
            ratio_prev = float('nan') # Inizializza a NaN per indicare che non è disponibile
            mean_prev_ratios = float('nan') # Inizializza a NaN
            deviation_from_previous = float('inf') 
            deviation_from_mean = float('inf') 

            # Calcolo deviazione dal tag precedente
            if pd.notna(ratios.loc[tag_prev_name]): # Controlla se il rapporto precedente esiste
                ratio_prev = ratios.loc[tag_prev_name]
                deviation_from_previous = abs(ratio_curr - ratio_prev)
            
            # Calcolo deviazione dalla media dei tag precedenti
            # Prendi i rapporti dei tag *precedenti* al tag corrente (da 0 a i-1)
            previous_tags_for_mean_ratios = ratios.iloc[:i].dropna()

            # Abbiamo bisogno di almeno un valore valido per calcolare la media
            if len(previous_tags_for_mean_ratios) > 0:
                mean_prev_ratios = previous_tags_for_mean_ratios.mean()
                deviation_from_mean = abs(ratio_curr - mean_prev_ratios)

            # --- VERIFICA ENTRAMBE LE CONDIZIONI ---
            # Si verificherà che deviation_from_previous e deviation_from_mean
            # non siano 'inf' (cioè siano stati calcolati) E che superino le soglie.
            if (deviation_from_previous != float('inf') and deviation_from_previous > threshold_previous and
                deviation_from_mean != float('inf') and deviation_from_mean > threshold_mean):

                if file_path not in file_deviations:
                    file_deviations[file_path] = []
                
                file_deviations[file_path].append({
                    "tag_current": tag_curr_name,
                    "tag_previous": tag_prev_name, 
                    "ratio_current": ratio_curr,
                    "ratio_previous": ratio_prev, # Qui ratio_previous potrebbe essere NaN se non esisteva
                    "mean_previous_ratios": mean_prev_ratios, # Qui mean_previous_ratios potrebbe essere NaN se non calcolato
                    "deviation_from_previous": deviation_from_previous,
                    "deviation_from_mean": deviation_from_mean
                })
                        
    if not file_deviations:
        _print(f"Nessun cambiamento significativo (rispetto alla media E al precedente) è stato trovato sopra le soglie: Media={threshold_mean}, Precedente={threshold_previous}.")
    else:
        
        _print(f"Trovate {len(file_deviations)} file con cambiamenti significativi (rispetto alla media E al precedente) sopra le soglie: Media={threshold_mean}, Precedente={threshold_previous}.\n")
        
        # Prova a leggere il file max_line_length_report.csv per ottenere le lunghezze massime delle righe
        calculate_max_line_length = False
        try:
            # Leggi il file max_line_length.csv per ottenere le lunghezze massime delle righe
            max_line_length_df = pd.read_csv(csv_path.replace("blank_space_ratio_report.csv", "max_line_length_report.csv"), index_col=0)
            
            if max_line_length_df.empty:
                raise Exception("Il file max_line_length_report.csv è vuoto o non è stato trovato.")
            
            calculate_max_line_length = True
        except:
            _print("Errore durante la lettura del file max_line_length_report.csv. Assicurati che il file esista e sia formattato correttamente.")
        
        total_deviations_found = 0
        for file_path, deviations_list in file_deviations.items():
            
            _print(f"--FILE: {file_path}\n")
            for dev_info in deviations_list:
                # Prepara i dati per la tabella
                prev_tag = dev_info['tag_previous']
                curr_tag = dev_info['tag_current']
                prev_ratio = f"{dev_info['ratio_previous']:.4f}" if pd.notna(dev_info['ratio_previous']) else "N/A"
                curr_ratio = f"{dev_info['ratio_current']:.4f}" if pd.notna(dev_info['ratio_current']) else "N/A"

                # Se disponibile, prendi la lunghezza massima della riga per entrambi i tag
                max_length_prev = max_length_curr = "N/A"
                if calculate_max_line_length and file_path in max_line_length_df.index:
                    prev_col = f"{prev_tag}_max_line_length"
                    curr_col = f"{curr_tag}_max_line_length"
                    if prev_col in max_line_length_df.columns:
                        max_length_prev = max_line_length_df.loc[file_path, prev_col]
                    if curr_col in max_line_length_df.columns:
                        max_length_curr = max_line_length_df.loc[file_path, curr_col]

                # Stampa la tabella solo con ratio e max line length
                _print(f"{'':<28}|{prev_tag:<20}|{curr_tag:<20}|{'DIFFERENCE (ABS)':<20}")
                _print(f"{'-'*28}|{'-'*20}|{'-'*20}|{'-'*20}")
                _print(f"{'Blank space ratio':<28}|{prev_ratio:<20}|{curr_ratio:<20}|{abs(dev_info['deviation_from_previous']):<20}")
                _print(f"{'Max line length':<28}|{max_length_prev:<20}|{max_length_curr:<20}|{abs(max_length_curr-max_length_prev):<20}")
                
                _print("")                        
                    
                total_deviations_found += 1
            _print("#" * 80)

    _print(f"Analisi completata. {total_deviations_found} deviazioni significative trovate.")

# --- Esempio di utilizzo ---
if __name__ == "__main__":
    
    # Parser per argomenti da linea di comando
    parser = argparse.ArgumentParser(description="Analizza il rapporto spazi bianchi nei file di un repository.")
    parser.add_argument("repo_url", help="URL del repository da analizzare")
    parser.add_argument("-e", "--extension", default=None, help="Estensione dei file da analizzare (es: py, js, txt). Se non specificata, analizza tutti i file di testo.")
    parser.add_argument("-sm", "--threshold_mean", type=float, default=1.0, 
                        help="Soglia di deviazione per la media dei rapporti precedenti. Default è 2.0.")
    parser.add_argument("-sp", "--threshold_previous", type=float, default=1.0, 
                        help="Soglia di deviazione per il rapporto del tag precedente. Default è 1.0.")
    parser.add_argument("-n", "--num-empty-chars", default=600, help="Numero di caratteri vuoti da aggiungere prima della vulnerabilità")
    args = parser.parse_args()

    repo_url = args.repo_url
    repo_name = repo_url.rstrip('/').split('/')[-1]
    repo_name = repo_name.split('.git')[0]  # Rimuovi .git se presente

    repo = clone_repo(repo_url)
    repo_path = repo.working_tree_dir
    
    # Esegui la manipolazione locale del repository (se necessario)
    # NOTA: Assicurati che perform_local_git_manipulation accetti l'argomento 'filters'
    edited_file_path = perform_local_git_manipulation(
        repo_path, 
        file_extension=args.extension if args.extension else ".py", 
        filters=filter,
        n_blank_chars=int(args.num_empty_chars)
    )

    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Current directory: {current_dir}")

    output_dir = os.path.join(current_dir, "analytics", repo_name)
    os.makedirs(output_dir, exist_ok=True)
    
    # Stampa i percorsi di output
    output_max_line_length_csv = os.path.join(output_dir, f"{repo_name}_max_line_length_report.csv")
    print(f"output_max_line_length_csv: {output_max_line_length_csv}")
    output_ratio_csv = os.path.join(output_dir, f"{repo_name}_blank_space_ratio_report.csv")
    print(f"output_ratio_csv: {output_ratio_csv}")
    output_log = os.path.join(output_dir, f"{repo_name}_blank_space_ratio_report.log")
    print(f"Output Log: {output_log}")
    
    # Analizza il repository per calcolare il blank_space_ratio e max_line_length
    analyze_repo_blank_space_ratio(repo, repo_path, args.extension, output_ratio_csv, output_max_line_length_csv)
    
    # Passa le due soglie separate
    analyze_blank_space_ratio_changes(output_ratio_csv, args.threshold_mean, args.threshold_previous, output_log)
    
    edited_file_last_line_n = None
    if edited_file_path and os.path.exists(edited_file_path):
        with open(edited_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            edited_file_last_line_n = len(lines)
        print(f"Il file a cui è stata aggiunta una \"backdoor\": {edited_file_path}:{edited_file_last_line_n}")
    else:
        print("Il file modificato non è stato trovato o l'operazione di manipolazione non è riuscita.")