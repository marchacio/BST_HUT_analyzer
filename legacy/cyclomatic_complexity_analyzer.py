import os
import ast

from ..src.utils.log import log

# We count decision points: if, for, while, except, and, or, assert, case, comprehensions.
class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor class to calculate cyclomatic complexity."""
    def __init__(self):
        # Initialize base complexity to 1 (for the entry point).
        self.complexity = 1

    def visit_If(self, node):
        # Counts the 'if' and each 'elif'. 'else' does not add structural complexity.
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # When visiting a function/method, complexity is calculated within its own scope.
        # We don't add complexity here, but we visit the function's body.
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Each 'and' or 'or' adds complexity. The number of operators is len(node.values) - 1.
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_match_case(self, node):
        # Each 'case' in a match statement (Python 3.10+) adds complexity.
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node):
        # Each loop ('for') or condition ('if') in a comprehension adds complexity.
        self.complexity += 1 + len(node.ifs)
        self.generic_visit(node)


def analyze_file_complexity(code: str, file_path: str) -> list[dict]:
    """
    Analyzes a single Python file to calculate the cyclomatic complexity
    of the module and each function/method within it.

    Args:
        code: The content of the Python file to analyze.
        file_path: The path of the Python file to analyze.

    Returns:
        A list of dictionaries, where each dictionary represents a code
        unit (module, function, method) and its complexity:
        {'name': str, 'type': str, 'complexity': int, 'line': int, 'file': str}.
    """
    complexities = []
    try:
        # Works only with Python source code
        tree = ast.parse(code)

        # Calculate complexity for the entire module
        module_visitor = ComplexityVisitor()
        module_visitor.visit(tree)
        complexities.append({
            'name': os.path.basename(file_path),
            'type': 'module',
            'complexity': module_visitor.complexity,
            'line': 1,
            'file': file_path
        })

        # Calculate complexity for each function and method
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_visitor = ComplexityVisitor()
                # Visit only the body of the function/method
                for item in node.body:
                    function_visitor.visit(item)

                complexities.append({
                    'name': node.name,
                    'type': 'function' if isinstance(node, ast.FunctionDef) else 'async function',
                    'complexity': function_visitor.complexity,
                    'line': node.lineno,
                    'file': file_path
                })

    except FileNotFoundError:
        log(f"Error: File not found {file_path}")
    except SyntaxError as e:
        if file_path and file_path.endswith('.py'):
            log(f"[CC] Warning: Syntax error in file {file_path}: {e}")
    except Exception as e:
        log(f"An unexpected error occurred while analyzing {file_path}: {e}")

    return complexities