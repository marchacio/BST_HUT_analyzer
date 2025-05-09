import ast

# Definizione estesa dei pattern di funzioni potenzialmente insicure da cercare
# Mappiamo il pattern (Modulo.funzione o solo funzione) alla sua gravità e descrizione
INSECURE_CALL_PATTERNS = [
    # --- High Severity Patterns ---
    {'severity': 'High', 'module': None, 'function': 'eval', 'description': 'Uso diretto di eval() - Rischio di esecuzione codice arbitrario (RCE).'},
    {'severity': 'High', 'module': None, 'function': 'exec', 'description': 'Uso diretto di exec() - Rischio di esecuzione codice arbitrario (RCE).'},

    # Deserializzazione insicura
    {'severity': 'High', 'module': 'pickle', 'function': 'load', 'description': 'Deserializzazione insicura con pickle.load() - Rischio di esecuzione codice (RCE).'},
    {'severity': 'High', 'module': 'pickle', 'function': 'loads', 'description': 'Deserializzazione insicura con pickle.loads() - Rischio di esecuzione codice (RCE).'},
    {'severity': 'High', 'module': 'yaml', 'function': 'load', 'description': 'Deserializzazione potenzialmente insicura con yaml.load() (usare Loader=yaml.SafeLoader) - Rischio di esecuzione codice (RCE).'}, # In PyYAML < 5.1 è insicuro di default

    # Esecuzione di comandi di sistema o sottoprocessi con shell=True
    {'severity': 'High', 'module': 'subprocess', 'function': 'Popen', 'description': 'subprocess.Popen() con shell=True - Rischio di Command Injection.', 'args_check': {'shell': True}},
    {'severity': 'High', 'module': 'subprocess', 'function': 'run', 'description': 'subprocess.run() con shell=True - Rischio di Command Injection.', 'args_check': {'shell': True}},
    {'severity': 'High', 'module': 'os', 'function': 'system', 'description': 'Esecuzione di comandi di sistema con os.system() - Rischio di Command Injection.'},
    {'severity': 'High', 'module': 'os', 'function': 'popen', 'description': 'Esecuzione di comandi di sistema con os.popen() - Rischio di Command Injection.'},
    {'severity': 'High', 'module': 'commands', 'function': 'getoutput', 'description': 'Esecuzione di comandi con commands.getoutput() (obsoleto) - Rischio di Command Injection.'}, # Modulo obsoleto in Python 3
    {'severity': 'High', 'module': 'commands', 'function': 'getstatusoutput', 'description': 'Esecuzione di comandi con commands.getstatusoutput() (obsoleto) - Rischio di Command Injection.'},

    # Vulnerabilità XXE (XML External Entity) nei parser standard non sicuri
    {'severity': 'High', 'module': 'xml.etree.ElementTree', 'function': 'parse', 'description': 'xml.etree.ElementTree.parse() - Rischio XXE con input non attendibile.'},
    {'severity': 'High', 'module': 'xml.etree.ElementTree', 'function': 'fromstring', 'description': 'xml.etree.ElementTree.fromstring() - Rischio XXE con input non attendibile se il parser supporta entità esterne.'},
    {'severity': 'High', 'module': 'xml.sax', 'function': 'parse', 'description': 'xml.sax.parse() - Rischio XXE con input non attendibile.'},
    {'severity': 'High', 'module': 'xml.dom.minidom', 'function': 'parse', 'description': 'xml.dom.minidom.parse() - Rischio XXE con input non attendibile.'},
    {'severity': 'High', 'module': 'xml.dom.pulldom', 'function': 'parse', 'description': 'xml.dom.pulldom.parse() - Rischio XXE con input non attendibile.'},
    {'severity': 'High', 'module': 'xml.dom.pulldom', 'function': 'parseString', 'description': 'xml.dom.pulldom.parseString() - Rischio XXE con input non attendibile.'},
    {'severity': 'High', 'module': 'xml.sax.expatreader', 'function': 'create_parser', 'description': 'xml.sax.expatreader.create_parser() - Rischio XXE con input non attendibile se non configurato per disabilitare entità.'},

    # Uso di hash deboli per scopi di sicurezza (es. password)
    {'severity': 'High', 'module': 'hashlib', 'function': 'md5', 'description': 'Uso di MD5 (hash debole) - Rischio di collisioni per verifiche di integrità o password.'},
    {'severity': 'High', 'module': 'hashlib', 'function': 'sha1', 'description': 'Uso di SHA1 (hash debole) - Rischio di collisioni per verifiche di integrità o password.'},

    # Creazione di file temporanei non sicuri
    {'severity': 'High', 'module': 'tempfile', 'function': 'mktemp', 'description': 'Uso di tempfile.mktemp() - Vulnerabile a race condition.'},

    # --- Medium Severity Patterns ---
    # Potenziale SSRF o connessioni insicure se l'URL/host è controllato dall'utente
    {'severity': 'Medium', 'module': 'urllib.request', 'function': 'urlopen', 'description': 'urllib.request.urlopen() - Potenziale SSRF se l\'URL è controllato dall\'utente.'},
    {'severity': 'Medium', 'module': 'requests', 'function': 'get', 'description': 'requests.get() - Potenziale SSRF se l\'URL è controllato dall\'utente o connessione insicura se SSL disabilitato.'},
    {'severity': 'Medium', 'module': 'requests', 'function': 'post', 'description': 'requests.post() - Potenziale SSRF se l\'URL è controllato dall\'utente o connessione insicura se SSL disabilitato.'},
    {'severity': 'Medium', 'module': 'requests', 'function': 'put', 'description': 'requests.put() - Potenziale SSRF se l\'URL è controllato dall\'utente o connessione insicura se SSL disabilitato.'},
    {'severity': 'Medium', 'module': 'requests', 'function': 'delete', 'description': 'requests.delete() - Potenziale SSRF se l\'URL è controllato dall\'utente o connessione insicura se SSL disabilitato.'},
    {'severity': 'Medium', 'module': 'requests', 'function': 'patch', 'description': 'requests.patch() - Potenziale SSRF se l\'URL è controllato dall\'utente o connessione insicura se SSL disabilitato.'},
    {'severity': 'Medium', 'module': 'requests', 'function': 'head', 'description': 'requests.head() - Potenziale SSRF se l\'URL è controllato dall\'utente o connessione insicura se SSL disabilitato.'},
    {'severity': 'Medium', 'module': 'requests', 'function': 'options', 'description': 'requests.options() - Potenziale SSRF se l\'URL è controllato dall\'utente o connessione insicura se SSL disabilitato.'},
    {'severity': 'Medium', 'module': 'ftplib', 'function': 'FTP', 'description': 'ftplib.FTP() - Connessione FTP potenzialmente insicura (non criptata).'},
    {'severity': 'Medium', 'module': 'smtplib', 'function': 'SMTP', 'description': 'smtplib.SMTP() - Connessione SMTP potenzialmente insicura (non criptata senza STARTTLS/SSL).'},
    {'severity': 'Medium', 'module': 'poplib', 'function': 'POP3', 'description': 'poplib.POP3() - Connessione POP3 potenzialmente insicura (non criptata senza SSL).'},
    {'severity': 'Medium', 'module': 'imaplib', 'function': 'IMAP4', 'description': 'imaplib.IMAP4() - Connessione IMAP4 potenzialmente insicura (non criptata senza SSL).'},
     {'severity': 'Medium', 'module': 'socket', 'function': 'create_connection', 'description': 'socket.create_connection() - Potenziale connessione a servizi interni se l\'host è controllato dall\'utente.'},


    # Uso di algoritmi crittografici obsoleti o configurazioni potenzialmente deboli
    {'severity': 'Medium', 'module': 'cryptography.hazmat.primitives.ciphers', 'function': 'Cipher', 'description': 'Uso di primitive crittografiche di basso livello (verifica la configurazione sicura: algoritmo, modalità, padding).'}, # Richiede analisi più profonda degli argomenti
    {'severity': 'Medium', 'module': 'ssl', 'function': 'wrap_socket', 'description': 'Uso diretto di ssl.wrap_socket() - Verifica la configurazione sicura (protocollo, cipher suites).'},
    {'severity': 'Medium', 'module': 'ssl', 'function': 'create_default_context', 'description': 'Uso di ssl.create_default_context() - Verifica che non vengano disabilitati controlli di sicurezza (check_hostname=False, verify_mode=CERT_NONE).'}, # Richiede analisi argomenti

    # Creazione di file temporanei con permessi potenzialmente insicuri
    {'severity': 'Medium', 'module': 'tempfile', 'function': 'mkstemp', 'description': 'Uso di tempfile.mkstemp() - Verifica che i permessi siano impostati correttamente (specialmente su sistemi multi-utente).'}, # Meno rischioso di mktemp, ma merita attenzione

    # --- Low Severity Patterns ---
    # Uso di generatori di numeri casuali non crittograficamente sicuri per scopi di sicurezza
    {'severity': 'Low', 'module': 'random', 'function': 'random', 'description': 'Uso di random.random() - Non adatto per scopi crittograficamente sicuri (usare il modulo secrets).'},
    {'severity': 'Low', 'module': 'random', 'function': 'randint', 'description': 'Uso di random.randint() - Non adatto per scopi crittograficamente sicuri (usare il modulo secrets).'},
    {'severity': 'Low', 'module': 'random', 'function': 'choice', 'description': 'Uso di random.choice() - Non adatto per scopi crittograficamente sicuri (usare il modulo secrets).'},
    {'severity': 'Low', 'module': 'random', 'function': 'randrange', 'description': 'Uso di random.randrange() - Non adatto per scopi crittograficamente sicuri (usare il modulo secrets).'},
    {'severity': 'Low', 'module': 'random', 'function': 'sample', 'description': 'Uso di random.sample() - Non adatto per scopi crittograficamente sicuri (usare il modulo secrets).'},
     {'severity': 'Low', 'module': 'random', 'function': 'shuffle', 'description': 'Uso di random.shuffle() - Non adatto per scopi crittograficamente sicuri (usare il modulo secrets).'},


    # Gestione di dati che potrebbe indicare informazioni sensibili (informativo)
    {'severity': 'Low', 'module': 'base64', 'function': 'b64encode', 'description': 'Uso di base64.b64encode() - Potrebbe indicare gestione di dati sensibili (informativo).'},
    {'severity': 'Low', 'module': 'base64', 'function': 'b64decode', 'description': 'Uso di base64.b64decode() - Potrebbe indicare gestione di dati sensibili (informativo).'},
    {'severity': 'Low', 'module': 'binascii', 'function': 'a2b_base64', 'description': 'Uso di binascii.a2b_base64() - Potrebbe indicare gestione di dati sensibili (informativo).'},
    {'severity': 'Low', 'module': 'binascii', 'function': 'b2a_base64', 'description': 'Uso di binascii.b2a_base64() - Potrebbe indicare gestione di dati sensibili (informativo).'},
    {'severity': 'Low', 'module': 'urllib.parse', 'function': 'quote', 'description': 'Uso di urllib.parse.quote() - Potrebbe essere necessario verificare la corretta gestione degli input per evitare problemi di URL encoding.'},
    {'severity': 'Low', 'module': 'urllib.parse', 'function': 'unquote', 'description': 'Uso di urllib.parse.unquote() - Potrebbe essere necessario verificare la corretta gestione degli input decodificati.'},

    # Potenziale esposizione di informazioni nei log/output (molto euristico)
    {'severity': 'Low', 'module': None, 'function': 'print', 'description': 'Uso di print() - Potenziale esposizione di informazioni sensibili nei log/output.'},
    {'severity': 'Low', 'module': 'logging', 'function': 'debug', 'description': 'Uso di logging.debug() - Assicurarsi che le informazioni sensibili non vengano loggate in modalità debug in produzione.'},
    {'severity': 'Low', 'module': 'logging', 'function': 'info', 'description': 'Uso di logging.info() - Assicurarsi che le informazioni sensibili non vengano loggate.'},

    # Uso di funzioni deprecate o con alternative più sicure
    {'severity': 'Low', 'module': 'os', 'function': 'tempnam', 'description': 'Uso di os.tempnam() - Deprecato e vulnerabile a race condition (usare il modulo tempfile).'},
    {'severity': 'Low', 'module': 'os', 'function': 'tmpfile', 'description': 'Uso di os.tmpfile() - Deprecato (usare tempfile.TemporaryFile).'},

    # Pattern specifici di framework o librerie che indicano potenziali debolezze (esempi concettuali)
    # {'severity': 'Low', 'module': 'django.conf.urls', 'function': 'url', 'description': 'Uso di django.conf.urls.url() - Deprecato, usare re_path().'}, # Esempio Django (deprecato)
    # {'severity': 'Low', 'module': 'flask', 'function': 'Flask', 'description': 'Inizializzazione app Flask con debug=True - Non adatto per produzione.', 'args_check': {'debug': True}}, # Richiede analisi argomenti per Flask

]


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
                module_name = None # Aggiunto per catturare il nome del modulo

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

                # Ora iteriamo sulla LISTA di pattern
                for pattern in INSECURE_CALL_PATTERNS:
                    is_potential_match = False
                    pattern_full_name = pattern.get('function') # Nome funzione nel pattern

                    # Costruisci il nome completo del pattern per confronto
                    if pattern.get('module'):
                         pattern_full_name = f"{pattern['module']}.{pattern['function']}"

                    # Verifica se il nome della funzione chiamata corrisponde al pattern corrente
                    if full_func_name == pattern_full_name:
                         is_potential_match = True

                    if is_potential_match:
                        is_actual_match = True # Presumi una corrispondenza a meno di specifici controlli sugli argomenti

                        # Controlla se il pattern richiede una verifica sugli argomenti
                        if 'args_check' in pattern:
                            # Per ogni argomento richiesto nel pattern
                            for arg_name, arg_value in pattern['args_check'].items():
                                # Se la verifica dell'argomento fallisce, non è un match effettivo
                                if not check_call_arguments(node, arg_name, arg_value):
                                    is_actual_match = False
                                    break # Non c'è bisogno di controllare altri argomenti per questo pattern

                        if is_actual_match:
                            findings.append({
                                'type': full_func_name, # O pattern_full_name, sono uguali in questo caso
                                'severity': pattern['severity'],
                                'line': node.lineno,
                                'description': pattern['description'],
                                'file': file_path
                            })
                            # Una volta trovato un match per questo nodo con questo pattern,
                            # potremmo voler interrompere la ricerca di altri pattern per lo stesso nodo
                            # per evitare duplicati se un nodo corrispondesse a più pattern (meno probabile con questa lista)
                            # break # Rimuovi il commento se vuoi solo il primo match per nodo

    except FileNotFoundError:
        # Già gestito da os.walk se il file scompare durante la scansione
        pass
    except SyntaxError as e:
        # Controlla esplicitamente se è un file .py prima di stampare l'avviso
        if file_path and file_path.endswith('.py'):
             print(f"Attenzione: Errore di sintassi nel file {file_path}: {e}")
    except Exception as e:
        # Cattura altri potenziali errori di parsing
        print(f"Si è verificato un errore inatteso durante l'analisi di {file_path}: {e}")

    return findings