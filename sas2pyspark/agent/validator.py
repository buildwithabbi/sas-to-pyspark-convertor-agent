import ast
from typing import Tuple, List


class PySparkValidator:
    """Validates generated PySpark python code for syntax correctness and structural validity."""

    @staticmethod
    def validate_code(python_code: str) -> Tuple[bool, List[str]]:
        """Parses python code using AST to check for syntax errors."""
        errors = []
        try:
            ast.parse(python_code)
            return True, []
        except SyntaxError as e:
            errors.append(f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}")
            return False, errors
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return False, errors
