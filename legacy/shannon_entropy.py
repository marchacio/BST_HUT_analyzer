import math
from collections import Counter

def calculate_shannon_entropy(data: bytes) -> float:
    """
    Calculates the Shannon entropy for a sequence of bytes.

    Args:
        data: The byte sequence for which to calculate the entropy.

    Returns:
        The entropy value in bits per byte. Returns 0.0 if the data is empty.
    """
    if not data:
        return 0.0

    # Count the frequency of each byte
    counts = Counter(data)
    total_length = len(data)
    entropy = 0.0

    # Calculate the entropy using the formula H = -sum(p_i * log2(p_i))
    for count in counts.values():
        probability = count / total_length
        # log2(0) is undefined, but p*log(p) -> 0 as p->0, so we skip it.
        if probability > 0:
            entropy -= probability * math.log2(probability)

    return entropy