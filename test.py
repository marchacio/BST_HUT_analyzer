import os
import pandas as pd

def analizza_caratteri_unicode(cartella_principale="analytics"):
    """
    Analizza i file unicodeanalyzer_hidden_chars.csv e unicodeanalyzer_homoglyphs.csv
    in tutte le sottocartelle per contare progetti e versioni con caratteri speciali.
    Include anche i totali di progetti e versioni analizzate.

    Args:
        cartella_principale (str): Il percorso della cartella "analytics".

    Returns:
        tuple: Un tuple contenente:
            - int: Il numero totale di progetti con caratteri speciali.
            - int: Il numero totale di versioni con caratteri speciali.
            - int: Il numero totale di progetti analizzati.
            - int: Il numero totale di versioni analizzate.
    """
    progetti_con_caratteri_speciali = set()
    versioni_con_caratteri_speciali = 0
    
    progetti_totali_analizzati = set()
    versioni_totali_analizzate = 0

    for root, dirs, files in os.walk(cartella_principale):
        if os.path.basename(root) == "unicode":
            # Siamo nella cartella "unicode" di un progetto X
            cartella_progetto_X = os.path.dirname(root)
            nome_progetto_X = os.path.basename(cartella_progetto_X)
            
            progetti_totali_analizzati.add(nome_progetto_X) # Aggiunge il progetto al totale

            file_hidden_chars = os.path.join(root, "unicodeanalyzer_hidden_chars.csv")
            file_homoglyphs = os.path.join(root, "unicodeanalyzer_homoglyphs.csv")

            dati_hidden = pd.DataFrame()
            dati_homoglyphs = pd.DataFrame()

            versioni_nel_progetto_corrente = set() # Per contare le versioni totali in questo progetto

            if os.path.exists(file_hidden_chars):
                try:
                    dati_hidden = pd.read_csv(file_hidden_chars)
                    if not dati_hidden.empty:
                        # Aggiunge tutte le versioni da questo file
                        for index, row in dati_hidden.iterrows():
                            if len(row) > 0: # Assicurati che ci sia almeno una colonna
                                versioni_nel_progetto_corrente.add(row.iloc[0])
                except Exception as e:
                    print(f"Errore nella lettura di {file_hidden_chars}: {e}")

            if os.path.exists(file_homoglyphs):
                try:
                    dati_homoglyphs = pd.read_csv(file_homoglyphs)
                    if not dati_homoglyphs.empty:
                        # Aggiunge tutte le versioni da questo file
                        for index, row in dati_homoglyphs.iterrows():
                            if len(row) > 0: # Assicurati che ci sia almeno una colonna
                                versioni_nel_progetto_corrente.add(row.iloc[0])
                except Exception as e:
                    print(f"Errore nella lettura di {file_homoglyphs}: {e}")

            versioni_totali_analizzate += len(versioni_nel_progetto_corrente)

            # Combina i dati e identifica le versioni con caratteri speciali
            if not dati_hidden.empty or not dati_homoglyphs.empty:
                
                versioni_con_problemi_in_questo_progetto = set()

                if not dati_hidden.empty:
                    for index, row in dati_hidden.iterrows():
                        if len(row) > 1 and pd.to_numeric(row.iloc[1], errors='coerce') > 0:
                            versioni_con_problemi_in_questo_progetto.add(row.iloc[0])

                if not dati_homoglyphs.empty:
                    for index, row in dati_homoglyphs.iterrows():
                        if len(row) > 1 and pd.to_numeric(row.iloc[1], errors='coerce') > 0:
                            versioni_con_problemi_in_questo_progetto.add(row.iloc[0])

                if versioni_con_problemi_in_questo_progetto:
                    progetti_con_caratteri_speciali.add(nome_progetto_X)
                    versioni_con_caratteri_speciali += len(versioni_con_problemi_in_questo_progetto)
                    
    return (len(progetti_con_caratteri_speciali), versioni_con_caratteri_speciali, 
            len(progetti_totali_analizzati), versioni_totali_analizzate)

# --- Esecuzione dello script ---
if __name__ == "__main__":
    num_progetti_con_problemi, num_versioni_con_problemi, \
    num_progetti_totali, num_versioni_totali = analizza_caratteri_unicode()

    print(f"\n--- Risultati dell'analisi ---")
    print(f"Numero totale di progetti (M) con caratteri speciali: {num_progetti_con_problemi}")
    print(f"Numero totale di versioni (N) con caratteri speciali: {num_versioni_con_problemi}")
    print(f"---")
    print(f"Numero totale di progetti analizzati: {num_progetti_totali}")
    print(f"Numero totale di versioni analizzate: {num_versioni_totali}")