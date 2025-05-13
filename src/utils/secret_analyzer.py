import re

from .log import log

# Definizione dei pattern regex per cercare potenziali segreti hardcoded.
# Questi sono esempi comuni e non sono esaustivi.
# La rilevazione di segreti è intrinsecamente soggetta a falsi positivi e negativi.
# Pattern più sofisticati e specifici per tipo di segreto (es. chiavi AWS, token GitHub)
# richiederebbero regex più complessi e potenzialmente controlli di validità.
SECRET_PATTERNS = [
    # Pattern generico per password (cerca parole chiave comuni seguite da = o :)
    {'name': 'Password', 'severity': 'High', 'regex': r'(?i)pass(?:word)?\s*[=:]\s*[\'"]?([^\s\'"]{4,})', 'description': 'Potenziale password hardcoded (match di almeno 4 caratteri).'},
    {'name': 'API Key', 'severity': 'High', 'regex': r'(?i)api_?key\s*[=:]\s*[\'"]?([^\s\'"]{10,})', 'description': 'Potenziale chiave API hardcoded.'},
    {'name': 'Secret Key', 'severity': 'High', 'regex': r'(?i)secret_?key\s*[=:]\s*[\'"]?([^\s\'"]{10,})', 'description': 'Potenziale chiave segreta hardcoded.'},
    {'name': 'Bearer Token', 'severity': 'High', 'regex': r'(?i)bearer\s+([a-z0-9\-_~+/]{20,}=?)', 'description': 'Potenziale Bearer token hardcoded.'},
    {'name': 'Access Key ID', 'severity': 'High', 'regex': r'(A3T[A-Z0-9]|AKIA|AGIA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}', 'description': 'Potenziale AWS Access Key ID hardcoded.'},
    {'name': 'Secret Access Key', 'severity': 'High', 'regex': r'(?i)aws_?secret_?access_?key\s*[=:]\s*[\'"]?([A-Za-z0-9+/]{40})', 'description': 'Potenziale AWS Secret Access Key hardcoded.'},
    {'name': 'Private Key', 'severity': 'High', 'regex': r'-----BEGIN (RSA|DSA|EC|PGP|OPENSSH) PRIVATE KEY-----', 'description': 'Potenziale chiave privata hardcoded.'},
    {'name': 'SSH Private Key', 'severity': 'High', 'regex': r'ssh-rsa\s+([A-Za-z0-9+/]{100,}=+)', 'description': 'Potenziale chiave SSH privata hardcoded.'},
    {'name': 'GitHub Token', 'severity': 'High', 'regex': r'ghp_[0-9a-zA-Z]{36}', 'description': 'Potenziale token GitHub hardcoded (ghp_).'},
    {'name': 'Slack Token', 'severity': 'High', 'regex': r'xox[baprs]-[^"\s]+', 'description': 'Potenziale token Slack hardcoded (xox[baprs]-).'},
    # Aggiungi altri pattern specifici se necessario
    {'name': 'HTTP call', 'severity': 'Medium', 'regex': r'http[s]?://[^\s]+', 'description': 'Potenziale chiamata HTTP hardcoded.'},
]

def find_secrets_in_file(code:str, file_path:str) -> list[dict]:
    """
    Scansiona un singolo file alla ricerca di pattern di segreti hardcoded.

    Args:
        code: Il contenuto del file da scansionare.
        file_path: Il percorso del file da scansionare.

    Returns:
        Una lista di findings, dove ogni finding è un dizionario
        {'type': str, 'severity': 'High', 'description': str, 'file': str, 'match': str}.
    """
    secrets_found = []
    try:
        
        code = code.decode('utf-8', errors='ignore') if isinstance(code, bytes) else code
        
        # Leggiamo il file riga per riga
        for line_num, line in enumerate(code.splitlines(), start=1):
            # Applichiamo ogni pattern regex alla riga corrente
            for pattern_info in SECRET_PATTERNS:
                regex = pattern_info['regex']
                pattern_name = pattern_info['name']
                severity = pattern_info['severity']
                description = pattern_info['description']

                # Cerchiamo tutte le occorrenze del pattern nella riga
                # re.findall ritorna una lista di tutte le sottostringhe che corrispondono al pattern
                # o ai gruppi di cattura nel pattern. Usiamo un gruppo di cattura per il valore del segreto.
                matches = re.findall(regex, line)

                for match in matches:
                    # Se il pattern ha un gruppo di cattura, 'match' sarà il contenuto del gruppo.
                    # Altrimenti, 'match' sarà l'intera corrispondenza.
                    # Per i pattern con gruppi, 'match' potrebbe essere una tupla se ci sono più gruppi.
                    # Semplifichiamo prendendo la prima parte se è una tupla/lista, altrimenti l'intera stringa.
                    match_value = match
                    if isinstance(match, (tuple, list)):
                        match_value = match[0] if match else "" # Prendi il primo elemento se esiste

                    # Aggiungiamo il finding alla lista
                    secrets_found.append({
                        'type': pattern_name,
                        'severity': severity, # I segreti sono generalmente High
                        'description': description,
                        'file': file_path,
                        'line': line_num, # Numero di riga in cui è stato trovato il segreto
                        'match': match_value # Mostriamo il valore trovato
                    })

    except FileNotFoundError:
        log(f"Errore: File non trovato {file_path}")
    except Exception as e:
        log(f"Si è verificato un errore durante la scansione dei segreti in {file_path}: {e}")

    return secrets_found