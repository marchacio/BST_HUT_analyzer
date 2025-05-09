import math
from collections import Counter

def calculate_shannon_entropy(data: bytes) -> float:
    """
    Calcola l'entropia di Shannon per una sequenza di byte.

    Args:
        data: La sequenza di byte di cui calcolare l'entropia.

    Returns:
        Il valore dell'entropia in bit per byte. Ritorna 0.0 se i dati sono vuoti.
    """
    if not data:
        return 0.0

    # Contare la frequenza di ogni byte
    counts = Counter(data)
    total_length = len(data)
    entropy = 0.0

    # Calcolare l'entropia usando la formula H = -sum(p_i * log2(p_i))
    for count in counts.values():
        # p_i è la probabilità del byte i
        probability = count / total_length
        if probability > 0: # log2(0) è indefinito, ma p*log(p) -> 0 per p->0
            entropy -= probability * math.log2(probability)

    return entropy