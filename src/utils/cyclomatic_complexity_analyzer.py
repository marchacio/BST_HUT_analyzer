import os
import ast

# Classe visitatore AST per calcolare la complessità ciclomica
# Contiamo i punti decisionali: if, for, while, except, and, or, assert, case
class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        # Inizializziamo la complessità base a 1 (punto di ingresso)
        self.complexity = 1

    # Metodi visit_* per i nodi che aggiungono complessità

    def visit_If(self, node):
        # Conta l'if e ogni elif. L'else non aggiunge complessità strutturale.
        self.complexity += 1
        # Continua a visitare i nodi figli (test, body, orelse)
        self.generic_visit(node)

    def visit_For(self, node):
        # Conta il ciclo for
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        # Conta il ciclo while
        self.complexity += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Quando visitiamo una definizione di funzione o metodo,
        # la complessità calcolata all'interno di questo ramo AST
        # è la complessità di quella funzione/metodo.
        # Non aggiungiamo complessità qui, ma visitiamo il corpo della funzione.
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        # Come FunctionDef, ma per funzioni asincrone
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        # Conta ogni blocco except
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Ogni operatore 'and' o 'or' in una BoolOp aggiunge complessità
        # Il numero di operatori è len(node.values) - 1
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        # Conta ogni assert
        self.complexity += 1
        self.generic_visit(node)

    # Gestione dei match statement (Python 3.10+)
    def visit_match_case(self, node):
        # Ogni 'case' in un match statement aggiunge complessità
        self.complexity += 1
        self.generic_visit(node)

    # Gestione delle comprehension (list, set, dict, generator)
    def visit_comprehension(self, node):
        # Ogni ciclo (for) o condizione (if) all'interno di una comprehension aggiunge complessità
        self.complexity += 1 + len(node.ifs) # Conta il 'for' e ogni 'if' nella comprehension
        self.generic_visit(node)


# Funzione per analizzare un singolo file e calcolare la complessità
def analyze_file_complexity(code: str, file_path:str) -> list[dict]:
    """
    Analizza un singolo file Python per calcolare la complessità ciclomica
    del modulo e di ogni funzione/metodo al suo interno.

    Args:
        code: Il contenuto del file Python da analizzare.
        file_path: Il percorso del file Python da analizzare.

    Returns:
        Una lista di dizionari, dove ogni dizionario rappresenta un'unità
        di codice (modulo, funzione, metodo) e la sua complessità:
        {'name': str, 'type': str, 'complexity': int, 'line': int, 'file': str}.
    """
    complexities = []
    try:

        tree = ast.parse(code)

        # Calcola la complessità per l'intero modulo
        module_visitor = ComplexityVisitor()
        module_visitor.visit(tree)
        complexities.append({
            'name': os.path.basename(file_path), # Nome del file
            'type': 'module',
            'complexity': module_visitor.complexity,
            'line': 1, # La complessità del modulo inizia dalla riga 1
            'file': file_path
        })

        # Calcola la complessità per ogni funzione e metodo
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_visitor = ComplexityVisitor()
                # Visita solo il corpo della funzione/metodo
                for item in node.body:
                    function_visitor.visit(item)

                complexities.append({
                    'name': node.name,
                    'type': 'function' if isinstance(node, ast.FunctionDef) else 'async function',
                    'complexity': function_visitor.complexity,
                    'line': node.lineno,
                    'file': file_path
                })
            # Potresti voler gestire anche ast.ClassDef se vuoi analizzare la complessità
            # dei metodi all'interno delle classi in modo più specifico, ma ast.walk
            # visiterà comunque i FunctionDef/AsyncFunctionDef al loro interno.

    except FileNotFoundError:
        print(f"Errore: File non trovato {file_path}")
    except SyntaxError as e:
        if file_path and file_path.endswith('.py'):
            print(f"Attenzione: Errore di sintassi nel file {file_path}: {e}")
    except Exception as e:
        print(f"Si è verificato un errore inatteso durante l'analisi di {file_path}: {e}")

    return complexities