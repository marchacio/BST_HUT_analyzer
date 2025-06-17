import ast

from .log import log

# Extended definition of potentially insecure function patterns to search for.
# We map the pattern (Module.function or just function) to its severity and description.
INSECURE_CALL_PATTERNS = [
    # --- High Severity Patterns ---
    {'severity': 'High', 'module': None, 'function': 'eval', 'description': 'Direct use of eval() - Risk of Remote Code Execution (RCE).'},
    {'severity': 'High', 'module': None, 'function': 'exec', 'description': 'Direct use of exec() - Risk of Remote Code Execution (RCE).'},

    # Insecure Deserialization
    {'severity': 'High', 'module': 'pickle', 'function': 'load', 'description': 'Insecure deserialization with pickle.load() - Risk of RCE.'},
    {'severity': 'High', 'module': 'pickle', 'function': 'loads', 'description': 'Insecure deserialization with pickle.loads() - Risk of RCE.'},
    # In PyYAML < 5.1, yaml.load() is insecure by default.
    {'severity': 'High', 'module': 'yaml', 'function': 'load', 'description': 'Potentially insecure deserialization with yaml.load() (use Loader=yaml.SafeLoader) - Risk of RCE.'},

    # System command or subprocess execution with shell=True
    {'severity': 'High', 'module': 'subprocess', 'function': 'Popen', 'description': 'subprocess.Popen() with shell=True - Risk of Command Injection.', 'args_check': {'shell': True}},
    {'severity': 'High', 'module': 'subprocess', 'function': 'run', 'description': 'subprocess.run() with shell=True - Risk of Command Injection.', 'args_check': {'shell': True}},
    {'severity': 'High', 'module': 'os', 'function': 'system', 'description': 'System command execution with os.system() - Risk of Command Injection.'},
    {'severity': 'High', 'module': 'os', 'function': 'popen', 'description': 'System command execution with os.popen() - Risk of Command Injection.'},
    # The 'commands' module is deprecated in Python 3.
    {'severity': 'High', 'module': 'commands', 'function': 'getoutput', 'description': 'Command execution with commands.getoutput() (deprecated) - Risk of Command Injection.'},
    {'severity': 'High', 'module': 'commands', 'function': 'getstatusoutput', 'description': 'Command execution with commands.getstatusoutput() (deprecated) - Risk of Command Injection.'},

    # XXE (XML External Entity) vulnerabilities in standard insecure parsers
    {'severity': 'High', 'module': 'xml.etree.ElementTree', 'function': 'parse', 'description': 'xml.etree.ElementTree.parse() - XXE risk with untrusted input.'},
    {'severity': 'High', 'module': 'xml.etree.ElementTree', 'function': 'fromstring', 'description': 'xml.etree.ElementTree.fromstring() - XXE risk with untrusted input if the parser supports external entities.'},
    {'severity': 'High', 'module': 'xml.sax', 'function': 'parse', 'description': 'xml.sax.parse() - XXE risk with untrusted input.'},
    {'severity': 'High', 'module': 'xml.dom.minidom', 'function': 'parse', 'description': 'xml.dom.minidom.parse() - XXE risk with untrusted input.'},
    {'severity': 'High', 'module': 'xml.dom.pulldom', 'function': 'parse', 'description': 'xml.dom.pulldom.parse() - XXE risk with untrusted input.'},
    {'severity': 'High', 'module': 'xml.dom.pulldom', 'function': 'parseString', 'description': 'xml.dom.pulldom.parseString() - XXE risk with untrusted input.'},
    {'severity': 'High', 'module': 'xml.sax.expatreader', 'function': 'create_parser', 'description': 'xml.sax.expatreader.create_parser() - XXE risk with untrusted input if not configured to disable entities.'},

    # Use of weak hashes for security purposes (e.g., passwords)
    {'severity': 'High', 'module': 'hashlib', 'function': 'md5', 'description': 'Use of MD5 (weak hash) - Risk of collisions for integrity checks or passwords.'},
    {'severity': 'High', 'module': 'hashlib', 'function': 'sha1', 'description': 'Use of SHA1 (weak hash) - Risk of collisions for integrity checks or passwords.'},

    # Insecure temporary file creation
    {'severity': 'High', 'module': 'tempfile', 'function': 'mktemp', 'description': 'Use of tempfile.mktemp() - Vulnerable to race conditions.'},

    # --- Medium Severity Patterns ---
    # Potential SSRF or insecure connections if the URL/host is user-controlled
    {'severity': 'Medium', 'module': 'urllib.request', 'function': 'urlopen', 'description': 'urllib.request.urlopen() - Potential SSRF if the URL is user-controlled.'},
    {'severity': 'Medium', 'module': 'requests', 'function': 'get', 'description': 'requests.get() - Potential SSRF if URL is user-controlled or insecure connection if SSL is disabled.'},
    {'severity': 'Medium', 'module': 'requests', 'function': 'post', 'description': 'requests.post() - Potential SSRF if URL is user-controlled or insecure connection if SSL is disabled.'},
    {'severity': 'Medium', 'module': 'ftplib', 'function': 'FTP', 'description': 'ftplib.FTP() - Potentially insecure FTP connection (unencrypted).'},
    {'severity': 'Medium', 'module': 'smtplib', 'function': 'SMTP', 'description': 'smtplib.SMTP() - Potentially insecure SMTP connection (unencrypted without STARTTLS/SSL).'},
    {'severity': 'Medium', 'module': 'poplib', 'function': 'POP3', 'description': 'poplib.POP3() - Potentially insecure POP3 connection (unencrypted without SSL).'},
    {'severity': 'Medium', 'module': 'imaplib', 'function': 'IMAP4', 'description': 'imaplib.IMAP4() - Potentially insecure IMAP4 connection (unencrypted without SSL).'},
    {'severity': 'Medium', 'module': 'socket', 'function': 'create_connection', 'description': 'socket.create_connection() - Potential connection to internal services if the host is user-controlled.'},

    # Use of outdated cryptographic algorithms or potentially weak configurations
    {'severity': 'Medium', 'module': 'cryptography.hazmat.primitives.ciphers', 'function': 'Cipher', 'description': 'Use of low-level cryptographic primitives (verify secure configuration: algorithm, mode, padding).'},
    {'severity': 'Medium', 'module': 'ssl', 'function': 'wrap_socket', 'description': 'Direct use of ssl.wrap_socket() - Verify secure configuration (protocol, cipher suites).'},
    {'severity': 'Medium', 'module': 'ssl', 'function': 'create_default_context', 'description': 'Use of ssl.create_default_context() - Verify that security checks are not disabled (e.g., check_hostname=False, verify_mode=CERT_NONE).'},

    # Insecure temporary file creation with potentially insecure permissions
    {'severity': 'Medium', 'module': 'tempfile', 'function': 'mkstemp', 'description': 'Use of tempfile.mkstemp() - Verify permissions are set correctly (especially on multi-user systems).'},

    # --- Low Severity Patterns ---
    # Use of non-cryptographically secure random number generators for security purposes
    {'severity': 'Low', 'module': 'random', 'function': 'random', 'description': 'Use of random.random() - Not suitable for cryptographically secure purposes (use the secrets module).'},
    {'severity': 'Low', 'module': 'random', 'function': 'randint', 'description': 'Use of random.randint() - Not suitable for cryptographically secure purposes (use the secrets module).'},
    {'severity': 'Low', 'module': 'random', 'function': 'choice', 'description': 'Use of random.choice() - Not suitable for cryptographically secure purposes (use the secrets module).'},
    {'severity': 'Low', 'module': 'random', 'function': 'randrange', 'description': 'Use of random.randrange() - Not suitable for cryptographically secure purposes (use the secrets module).'},
    {'severity': 'Low', 'module': 'random', 'function': 'sample', 'description': 'Use of random.sample() - Not suitable for cryptographically secure purposes (use the secrets module).'},
    {'severity': 'Low', 'module': 'random', 'function': 'shuffle', 'description': 'Use of random.shuffle() - Not suitable for cryptographically secure purposes (use the secrets module).'},

    # Data handling that could indicate sensitive information (informational)
    {'severity': 'Low', 'module': 'base64', 'function': 'b64encode', 'description': 'Use of base64.b64encode() - May indicate handling of sensitive data (informational).'},
    {'severity': 'Low', 'module': 'base64', 'function': 'b64decode', 'description': 'Use of base64.b64decode() - May indicate handling of sensitive data (informational).'},
    {'severity': 'Low', 'module': 'urllib.parse', 'function': 'quote', 'description': 'Use of urllib.parse.quote() - May need to verify proper input handling to avoid URL encoding issues.'},
    {'severity': 'Low', 'module': 'urllib.parse', 'function': 'unquote', 'description': 'Use of urllib.parse.unquote() - May need to verify proper handling of decoded input.'},

    # Potential information exposure in logs/output (very heuristic)
    {'severity': 'Low', 'module': None, 'function': 'print', 'description': 'Use of print() - Potential exposure of sensitive information in logs/output.'},
    {'severity': 'Low', 'module': 'logging', 'function': 'debug', 'description': 'Use of logging.debug() - Ensure sensitive information is not logged in debug mode in production.'},
    {'severity': 'Low', 'module': 'logging', 'function': 'info', 'description': 'Use of logging.info() - Ensure sensitive information is not logged.'},

    # Use of deprecated functions or those with safer alternatives
    {'severity': 'Low', 'module': 'os', 'function': 'tempnam', 'description': 'Use of os.tempnam() - Deprecated and vulnerable to race conditions (use the tempfile module).'},
    {'severity': 'Low', 'module': 'os', 'function': 'tmpfile', 'description': 'Use of os.tmpfile() - Deprecated (use tempfile.TemporaryFile).'},
]

def check_call_arguments(node: ast.Call, required_arg_name: str, required_arg_value) -> bool:
    """
    Checks if an AST function call has a specific keyword argument
    with a specific constant value.
    (Only supports keyword arguments with simple constant values like True/False/None/strings/numbers)
    """
    for keyword in node.keywords:
        if keyword.arg == required_arg_name:
            # Check if the value is a constant and matches the required value
            if isinstance(keyword.value, ast.Constant) and keyword.value.value == required_arg_value:
                return True
    # For a more complete analysis, positional arguments and non-constant expressions
    # should also be checked, but this is much more complex.
    return False

def analyze_python_file_for_sast(code: str, file_path: str) -> list[dict]:
    """
    Analyzes a single Python source file for basic insecure patterns.

    Args:
        code: The source code of the Python file to analyze.
        file_path: The path of the Python file.

    Returns:
        A list of findings, where each finding is a dictionary:
        {'type': str, 'severity': str, 'line': int, 'description': str, 'file': str}.
    """
    findings = []
    try:
        tree = ast.parse(code, type_comments=True, filename=file_path)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                full_func_name = None
                
                if isinstance(func, ast.Name):
                    # Simple call: e.g., eval(...)
                    full_func_name = func.id
                elif isinstance(func, ast.Attribute):
                    # Attribute call: e.g., os.system(...)
                    # For simplicity, we only handle the 'module.function' case.
                    if isinstance(func.value, ast.Name):
                        module_name = func.value.id
                        function_name = func.attr
                        full_func_name = f"{module_name}.{function_name}"

                if not full_func_name:
                    continue

                for pattern in INSECURE_CALL_PATTERNS:
                    pattern_full_name = f"{pattern['module']}.{pattern['function']}" if pattern.get('module') else pattern.get('function')
                    
                    if full_func_name == pattern_full_name:
                        is_actual_match = True
                        
                        if 'args_check' in pattern:
                            is_actual_match = False  # Must be proven by argument check
                            for arg_name, arg_value in pattern['args_check'].items():
                                if check_call_arguments(node, arg_name, arg_value):
                                    is_actual_match = True
                                    break # Argument matched, so the pattern is a match

                        if is_actual_match:
                            findings.append({
                                'type': full_func_name,
                                'severity': pattern['severity'],
                                'line': node.lineno,
                                'description': pattern['description'],
                                'file': file_path
                            })
                            # Once a match is found, we could break to avoid multiple pattern matches for the same node.
                            # break

    except SyntaxError as e:
        if file_path and file_path.endswith('.py'):
             log(f"[SAST] Warning: Syntax error in file {file_path}: {e}")
    except Exception as e:
        log(f"An unexpected error occurred while analyzing {file_path}: {e}")

    return findings