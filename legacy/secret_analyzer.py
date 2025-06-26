import re

from ..src.utils.log import log

# Definition of regex patterns to search for potential hardcoded secrets.
# These are common examples and are not exhaustive.
# Secret detection is inherently prone to false positives and negatives.
# More sophisticated and secret-type-specific patterns (e.g., for AWS keys, GitHub tokens)
# would require more complex regex and potentially validity checks.
SECRET_PATTERNS = [
    # Generic pattern for passwords (looks for common keywords followed by = or :)
    {'name': 'Password', 'severity': 'High', 'regex': r'(?i)pass(?:word)?\s*[=:]\s*[\'"]?([^\s\'"]{4,})', 'description': 'Potential hardcoded password (matches at least 4 characters).'},
    {'name': 'API Key', 'severity': 'High', 'regex': r'(?i)api_?key\s*[=:]\s*[\'"]?([^\s\'"]{10,})', 'description': 'Potential hardcoded API key.'},
    {'name': 'Secret Key', 'severity': 'High', 'regex': r'(?i)secret_?key\s*[=:]\s*[\'"]?([^\s\'"]{10,})', 'description': 'Potential hardcoded secret key.'},
    {'name': 'Bearer Token', 'severity': 'High', 'regex': r'(?i)bearer\s+([a-z0-9\-_~+/]{20,}=?)', 'description': 'Potential hardcoded Bearer token.'},
    {'name': 'Access Key ID', 'severity': 'High', 'regex': r'(A3T[A-Z0-9]|AKIA|AGIA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}', 'description': 'Potential hardcoded AWS Access Key ID.'},
    {'name': 'Secret Access Key', 'severity': 'High', 'regex': r'(?i)aws_?secret_?access_?key\s*[=:]\s*[\'"]?([A-Za-z0-9+/]{40})', 'description': 'Potential hardcoded AWS Secret Access Key.'},
    {'name': 'Private Key', 'severity': 'High', 'regex': r'-----BEGIN (RSA|DSA|EC|PGP|OPENSSH) PRIVATE KEY-----', 'description': 'Potential hardcoded private key.'},
    {'name': 'SSH Private Key', 'severity': 'High', 'regex': r'ssh-rsa\s+([A-Za-z0-9+/]{100,}=+)', 'description': 'Potential hardcoded SSH private key.'},
    {'name': 'GitHub Token', 'severity': 'High', 'regex': r'ghp_[0-9a-zA-Z]{36}', 'description': 'Potential hardcoded GitHub token (ghp_).'},
    {'name': 'Slack Token', 'severity': 'High', 'regex': r'xox[baprs]-[^"\s]+', 'description': 'Potential hardcoded Slack token (xox[baprs]-).'},
    # Add other specific patterns if needed
    {'name': 'HTTP Call', 'severity': 'Medium', 'regex': r'http[s]?://[^\s]+', 'description': 'Potential hardcoded HTTP call.'},
]

def find_secrets_in_file(code: str, file_path: str) -> list[dict]:
    """
    Scans a single file for hardcoded secret patterns.

    Args:
        code: The content of the file to scan.
        file_path: The path of the file to scan.

    Returns:
        A list of findings, where each finding is a dictionary:
        {'type': str, 'severity': str, 'description': str, 'file': str, 'match': str}.
    """
    secrets_found = []
    try:
        # Ensure content is a string
        code = code.decode('utf-8', errors='ignore') if isinstance(code, bytes) else code
        
        for line_num, line in enumerate(code.splitlines(), start=1):
            for pattern_info in SECRET_PATTERNS:
                regex = pattern_info['regex']
                pattern_name = pattern_info['name']
                severity = pattern_info['severity']
                description = pattern_info['description']

                # re.findall returns a list of all substrings that match the pattern
                # or capture groups in the pattern.
                matches = re.findall(regex, line)

                for match in matches:
                    # If the pattern has a capture group, 'match' will be its content.
                    # Otherwise, 'match' will be the entire matching string.
                    # For patterns with multiple groups, 'match' could be a tuple.
                    # We simplify by taking the first item if it's a tuple/list.
                    match_value = match
                    if isinstance(match, (tuple, list)) and match:
                        match_value = match[0]

                    secrets_found.append({
                        'type': pattern_name,
                        'severity': severity,
                        'description': description,
                        'file': file_path,
                        'line': line_num,
                        'match': match_value
                    })

    except FileNotFoundError:
        log(f"Error: File not found {file_path}")
    except Exception as e:
        log(f"An error occurred while scanning for secrets in {file_path}: {e}")

    return secrets_found