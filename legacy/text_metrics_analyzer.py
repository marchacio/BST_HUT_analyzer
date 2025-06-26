from ..src.utils.log import log

def analyze_file_text_metrics(file_path: str, code: str) -> dict:
    """
    Analyzes a single file's content to calculate the length of the longest line
    and the ratio of blank spaces to total characters.

    Args:
        file_path (str): The path of the file being analyzed.
        code (str): The string content of the file.

    Returns:
        A dictionary containing the metrics:
        {'file': str, 'longest_line_length': int, 'blank_space_ratio': float, ...}
        Returns default values (0) in case of an error or empty content.
    """
    longest_line_length = 0
    total_chars = 0
    total_blank_spaces = 0

    try:
        for line in code.splitlines():
            # 1. Find the longest line
            current_line_length = len(line)
            if current_line_length > longest_line_length:
                longest_line_length = current_line_length

            # 2. Calculate total characters and blank spaces
            total_chars += current_line_length
            total_blank_spaces += line.count(' ') + line.count('\t')

    except Exception as e:
        log(f"[FILE_TEXT_METRICS] Error analyzing {file_path}: {e}")
        # Return empty results for this file in case of an error
        return {
            'file': file_path,
            'longest_line_length': 0,
            'blank_space_ratio': 0.0,
            'total_chars': 0,
            'total_blank_spaces': 0
        }

    # Calculate the ratio only if there are total characters to avoid division by zero
    blank_space_ratio = total_blank_spaces / total_chars if total_chars > 0 else 0.0

    return {
        'file': file_path,
        'longest_line_length': longest_line_length,
        'blank_space_ratio': blank_space_ratio,
        'total_chars': total_chars,
        'total_blank_spaces': total_blank_spaces
    }