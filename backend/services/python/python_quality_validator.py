import ast
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Strict allowlist of modules genuinely needed for analytical transformations
ALLOWED_MODULES = {
    "pandas", "numpy", "math", "statistics", "re", "json", "datetime", "collections"
}

# Dangerous calls to reject
DANGEROUS_CALLS = {
    "eval", "exec", "__import__", "globals", "locals"
}

def validate_python_code(code: str) -> Tuple[bool, str]:
    """
    Deterministically validates Python code using AST parsing.
    Checks:
    - Syntax correctness
    - Forbidden imports (anything not in ALLOWED_MODULES)
    - Dangerous builtins (eval, exec, etc.)
    Returns (is_valid, error_message)
    """
    try:
        root = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax Error: {e.msg} at line {e.lineno}, col {e.offset}"
    except Exception as e:
        return False, f"AST parsing failed: {e}"

    for node in ast.walk(root):
        # 1. Check imports (Import and ImportFrom)
        if isinstance(node, ast.Import):
            for name in node.names:
                base_module = name.name.split('.')[0]
                if base_module not in ALLOWED_MODULES:
                    return False, f"Import Violation: Module '{base_module}' is not in the whitelist of permitted libraries."
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base_module = node.module.split('.')[0]
                if base_module not in ALLOWED_MODULES:
                    return False, f"Import Violation: Module '{base_module}' is not in the whitelist of permitted libraries."
        
        # 2. Check call arguments and attributes for dangerous dynamic imports or builtins
        elif isinstance(node, ast.Call):
            # Checking direct builtin calls (e.g. exec(), eval())
            if isinstance(node.func, ast.Name):
                if node.func.id in DANGEROUS_CALLS:
                    return False, f"Security Violation: Use of forbidden function '{node.func.id}' is prohibited."
            
            # Checking getattr/dynamic attributes like getattr(..., '__import__')
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in DANGEROUS_CALLS:
                    return False, f"Security Violation: Accessing forbidden attribute '{node.func.attr}' is prohibited."

        # 3. Check name nodes (just in case exec/eval/globals are referenced or passed around)
        elif isinstance(node, ast.Name):
            if node.id in DANGEROUS_CALLS and not isinstance(node.ctx, ast.Store):
                return False, f"Security Violation: Reference to forbidden identifier '{node.id}' is prohibited."

    return True, ""
