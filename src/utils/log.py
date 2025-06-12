import logging
import os

def init_logging(log_file:str, save_file:bool, level=logging.INFO):
    """
    Inizializza il sistema di logging.
    Questa funzione deve essere chiamata una sola volta nel tuo script principale (main).

    Args:
        log_file (str): Il nome del file di log. Per default 'log.txt'.
        level (int): Il livello minimo di logging da registrare.
                     Esempi: logging.DEBUG, logging.INFO, logging.WARNING,
                             logging.ERROR, logging.CRITICAL.
    """
        
    # Crea un'istanza del logger. È buona pratica usare un nome specifico.
    # logging.getLogger() con lo stesso nome ritorna sempre la stessa istanza.
    global_logger = logging.getLogger('my_tool_logger')

    global_logger.setLevel(level) # Imposta il livello minimo di log per l'intero logger

    # Crea un formattatore per i messaggi di log
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    if save_file:
        # Se il file di log esiste già, lo cancella
        # per evitare di appendere i nuovi log a quelli vecchi.
        if os.path.exists(log_file):
            os.remove(log_file)
        else:
            # Crea il file se non esiste
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
                    
        # 1. Handler per il file di log
        # 'a' significa append, quindi i nuovi log verranno aggiunti alla fine del file esistente.
        # encoding='utf-8' assicura la corretta gestione dei caratteri speciali.
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        global_logger.addHandler(file_handler)

    # 2. Handler per la console (output standard)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    global_logger.addHandler(console_handler)

    # Messaggio di debug per confermare l'inizializzazione
    # Questo messaggio verrà mostrato solo se il 'level' è impostato a DEBUG o inferiore.
    global_logger.debug(f"Sistema di logging inizializzato. File di log: {os.path.abspath(log_file)}")
    return global_logger