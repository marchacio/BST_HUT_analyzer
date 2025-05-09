import os
import ast

# Definizione dei pattern di funzioni potenzialmente insicure da cercare
# Mappiamo il nome della funzione (o 'Modulo.funzione') alla sua gravità e descrizione
# Possiamo aggiungere qui altri pattern
INSECURE_PATTERNS = {
    'High': {
        'eval': 'Uso diretto di eval() - Rischio di esecuzione codice arbitrario.',
        'exec': 'Uso diretto di exec() - Rischio di esecuzione codice arbitrario.',
        'pickle.load': 'Deserializzazione insicura con pickle.load() - Rischio di esecuzione codice.',
        'pickle.loads': 'Deserializzazione insicura con pickle.loads() - Rischio di esecuzione codice.',
        'yaml.load': 'Deserializzazione potenzialmente insicura con yaml.load() (usare Loader=yaml.SafeLoader).', # In PyYAML < 5.1 è insicuro di default
        'subprocess.Popen': 'Esecuzione di sottoprocessi (verifica l\'uso di shell=True).', # Richiede verifica argomenti
        'subprocess.run': 'Esecuzione di sottoprocessi (verifica l\'uso di shell=True).',   # Richiede verifica argomenti
        'os.system': 'Esecuzione di comandi di sistema con os.system().',
        'os.popen': 'Esecuzione di comandi di sistema con os.popen().',
        # Aggiungi qui altre funzioni ad alta criticità
    },
    'Medium': {
        # Esempi ipotetici di pattern a media criticità (non inclusi nel codice di analisi AST qui sotto,
        # poiché richiederebbero logica di rilevamento diversa o più complessa)
        # 'base64.b64decode': 'Decodifica Base64 - potenziale parte di una catena di attacco.',
        # 'cryptography.hazmat.primitives.ciphers': 'Uso di primitive crittografiche (verifica la configurazione sicura).'
    },
    'Low': {
        # Esempi ipotetici di pattern a bassa criticità o informativi
        # 'print': 'Stampa di variabili non sanificate (potrebbe esporre dati sensibili in log/output).',
    }
}

# Funzione per verificare argomenti specifici in una chiamata di funzione AST
# Utile per casi come subprocess.run(..., shell=True)
def check_call_arguments(node: ast.Call, required_arg_name: str, required_arg_value) -> bool:
    """
    Controlla se una chiamata di funzione AST ha un argomento keyword specifico
    con un valore costante specifico.
    (Supporta solo argomenti keyword con valori costanti semplici come True/False/None/stringhe/numeri)
    """
    for keyword in node.keywords:
        if keyword.arg == required_arg_name:
            # Verifica se il valore è una costante e corrisponde al valore richiesto
            if isinstance(keyword.value, ast.Constant) and keyword.value.value == required_arg_value:
                return True
    # Per un'analisi più completa, si dovrebbero controllare anche gli argomenti posizionali
    # e analizzare espressioni non costanti, ma è molto più complesso.
    return False


# Analizzatore per singolo file
def analyze_python_file_for_sast(code: str, file_path:str) -> list[dict]:
    """
    Analizza un singolo file Python alla ricerca di pattern insicuri di base.

    Args:
        code: Il codice sorgente del file Python da analizzare;
        file_path: Il percorso del file Python.

    Returns:
        Una lista di findings, dove ogni finding è un dizionario
        {'type': str, 'severity': str, 'line': int, 'description': str, 'file': str}.
    """
    findings = []
    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):
            # Cerchiamo le chiamate a funzioni
            if isinstance(node, ast.Call):
                # Cerchiamo di ottenere il nome completo della funzione chiamata (es. 'eval', 'os.system', 'pickle.load')
                func = node.func
                full_func_name = None

                if isinstance(func, ast.Name):
                    # Chiamata semplice: es. eval(...)
                    full_func_name = func.id
                elif isinstance(func, ast.Attribute):
                    # Chiamata con attributo: es. os.system(...) or obj.method(...)
                    # Per semplicità, gestiamo solo il caso 'modulo.funzione'
                    if isinstance(func.value, ast.Name):
                        module_name = func.value.id
                        function_name = func.attr
                        full_func_name = f"{module_name}.{function_name}"
                    # Gestire casi più complessi (es. obj.sub.method) renderebbe il codice molto più complicato

                if full_func_name:
                    # Controlla se il nome della funzione chiamata corrisponde a un pattern insicuro
                    for severity, patterns in INSECURE_PATTERNS.items():
                        if full_func_name in patterns:
                            description = patterns[full_func_name]
                            is_match = True # Presumi una corrispondenza a meno di specifici controlli sugli argomenti

                            # Aggiungi controlli specifici per le funzioni che richiedono argomenti specifici per essere insicure
                            if full_func_name in ['subprocess.Popen', 'subprocess.run']:
                                # Richiede shell=True per essere considerato ad alta severità in questo contesto basilare
                                if not check_call_arguments(node, 'shell', True):
                                    is_match = False # Non è una chiamata con shell=True, non la segnialiamo come High qui

                            elif full_func_name == 'yaml.load':
                                # In PyYAML >= 5.1 è sicuro di default, ma il warning rimane per versioni precedenti
                                # Potresti aggiungere un check sugli argomenti se vuoi distinguere SafeLoader
                                pass # Per questo esempio base, segnialiamo ogni yaml.load come potenziale rischio

                            if is_match:
                                findings.append({
                                    'type': full_func_name,
                                    'severity': severity,
                                    'line': node.lineno,
                                    'description': description,
                                    'file': file_path
                                })
                                # Una volta trovato un match per questo nodo, non c'è bisogno di controllare altri pattern per la stessa chiamata
                                break


    except FileNotFoundError:
        # Già gestito da os.walk se il file scompare durante la scansione
        pass
    except SyntaxError as e:
        if file_path.endswith('.py'):
            print(f"Attenzione: Errore di sintassi nel file {file_path}: {e}")
    except Exception as e:
        # Cattura altri potenziali errori di parsing
        print(f"Si è verificato un errore inatteso durante l'analisi di {file_path}: {e}")

    return findings
