import unicodedata
import os
import regex # Importa la libreria regex

def get_unicode_script(char):
    """
    Restituisce il codice script ISO 15924 di un carattere usando la libreria regex.
    Questo funziona anche per versioni di Python < 3.9.
    """
    match = regex.match(r'\p{Script=([A-Za-z]+)}', char)
    if match:
        return match.group(1)
    return None # O un valore predefinito come 'Common' o 'Unknown' se preferisci

def is_homograph_or_uncommon(char, common_scripts=['Latn'], common_blocks=[], common_categories=[]):
    """
    Verifica se un carattere è considerato "non-comune" o un potenziale omografo
    basandosi su script, blocchi Unicode e categorie.
    AGGIORNATO per usare regex.
    """
    if not char.isprintable():  # Ignora caratteri di controllo non stampabili
        return False

    char_name = unicodedata.name(char, 'UNKNOWN')
    
    # 1. Controllo dello Script (usando regex)
    char_script = get_unicode_script(char)
    
    if common_scripts and char_script and char_script not in common_scripts:
        print(f"  - Carattere '{char}' (U+{ord(char):04X}) è di script '{char_script}', non in script comuni.")
        return True

    # 2. Controllo della Categoria Generale
    char_category = unicodedata.category(char)
    if common_categories and char_category not in common_categories:
        print(f"  - Carattere '{char}' (U+{ord(char):04X}) è di categoria '{char_category}', non in categorie comuni.")
        return True

    # 3. Controllo del Nome del Carattere per Omografi e Simboli Specifici
    if "GREEK" in char_name and 'Latn' in common_scripts:
        print(f"  - Carattere '{char}' (U+{ord(char):04X}) ha 'GREEK' nel nome e script comune è latino.")
        return True
    if "CYRILLIC" in char_name and 'Latn' in common_scripts:
        print(f"  - Carattere '{char}' (U+{ord(char):04X}) ha 'CYRILLIC' nel nome e script comune è latino.")
        return True

    return False

def find_uncommon_unicode_chars(filepath, common_scripts=['Latn'], common_blocks=[], common_categories=['Ll', 'Lu', 'Lt', 'Lm', 'Lo', 'Nd', 'Nl', 'No', 'Pc', 'Pd', 'Ps', 'Pe', 'Pi', 'Pf', 'Po', 'Sm', 'Sc', 'Sk', 'So']):
    """
    Scansiona un file di testo per trovare caratteri Unicode "non-comuni"
    o potenziali omografi basandosi sui criteri forniti.
    """
    uncommon_chars_found = {}

    if not os.path.exists(filepath):
        print(f"Errore: Il file '{filepath}' non esiste.")
        return uncommon_chars_found

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                for char in line:
                    if is_homograph_or_uncommon(char, common_scripts, common_blocks, common_categories):
                        if char not in uncommon_chars_found:
                            uncommon_chars_found[char] = []
                        uncommon_chars_found[char].append(line_num)
    except UnicodeDecodeError:
        _ = None # Ignora l'errore di decodifica Unicode
        # print(f"Errore di decodifica Unicode per il file '{filepath}'. Assicurati che sia UTF-8.")
    except Exception as e:
        print(f"Si è verificato un errore durante la lettura del file: {e}")

    return uncommon_chars_found

if __name__ == "__main__":
    # --- Configurazione ---
    my_common_scripts = ['Latn']
    my_common_blocks = []
    my_common_categories = [
        'Ll', 'Lu', # Lettere minuscole e maiuscole
        'Nd',       # Numeri decimali
        'Po', 'Ps', 'Pe', 'Pd', 'Pc', 'Pi', 'Pf', # Punteggiatura
        'Zs',       # Separatore di spazio
        'Sm', 'Sk', 'Sc'
    ]

    # Richiedi il percorso della cartella all'utente
    folder_path = input("Inserisci il percorso della cartella da analizzare: ").strip()

    # Ottieni tutti i file nella cartella (ricorsivamente, inclusi sottocartelle)
    file_list = []
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            file_list.append(os.path.join(root, f))

    print(f"Criteri per caratteri comuni:")
    print(f"  - Script comuni: {my_common_scripts}")
    print(f"  - Categorie comuni: {my_common_categories}")
    print("-" * 30)

    for test_file_name in file_list:

        uncommon_chars = find_uncommon_unicode_chars(
            test_file_name, 
            common_scripts=my_common_scripts,
            common_categories=my_common_categories
        )

        if uncommon_chars:
            print(f"\nAnalisi del file: {test_file_name}")
            print("\nCaratteri 'non-comuni' o omografi trovati:")
            for char, lines in uncommon_chars.items():
                char_name = unicodedata.name(char, "NOME SCONOSCIUTO")
                char_script = get_unicode_script(char)
                char_category = unicodedata.category(char)
                print(f"  - '{char}' (Unicode: U+{ord(char):04X}, Nome: '{char_name}', Script: '{char_script}', Categoria: '{char_category}') trovato nelle righe: {', '.join(map(str, sorted(set(lines))))}")
        #else:
            #print("\nNessun carattere 'non-comune' o omografo trovato secondo i criteri specificati.")