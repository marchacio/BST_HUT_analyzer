from .log import log

def analyze_file_text_metrics(file_path:str, code: str) -> dict:
    """
    Analizza un singolo file per calcolare la lunghezza della riga più lunga
    e il rapporto tra spazi vuoti e caratteri totali.

    Args:
        file_path: Il percorso del file da analizzare.

    Returns:
        Un dizionario contenente le metriche:
        {'file': str, 'longest_line_length': int, 'blank_space_ratio': float}
        Ritorna valori predefiniti (0.0) se il file non può essere letto o è vuoto.
    """
    longest_line_length = 0
    total_chars = 0
    total_blank_spaces = 0

    try:
        # Apri il file in modalità testo con gestione degli errori di codifica
        for line_num, line in enumerate(code.splitlines(), start=1):
            # 1. Conta la riga più lunga
            current_line_length = len(line)
            if current_line_length > longest_line_length:
                longest_line_length = current_line_length

            # 2. Calcola i caratteri totali e gli spazi vuoti
            total_chars += current_line_length
            # Conta spazi, tabulazioni, newline e carriage return
            total_blank_spaces += line.count(' ') + line.count('\t') + line.count('\n') + line.count('\r')


    except Exception as e:
        log(f"[FILE_TEXT_METRICS] {file_path}: {e}")
        # Ritorna risultati vuoti per questo file
        return {
            'file': file_path, 
            'longest_line_length': 0, 
            'blank_space_ratio': 0.0
        }

    # Calcola il rapporto solo se ci sono caratteri totali per evitare divisione per zero
    blank_space_ratio = total_blank_spaces / total_chars if total_chars > 0 else 0.0

    return {
        'file': file_path,
        'longest_line_length': longest_line_length,
        'blank_space_ratio': blank_space_ratio,
    }