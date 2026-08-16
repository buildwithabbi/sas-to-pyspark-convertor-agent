import re


class SASFunctionMapper:
    """Maps SAS functions and expressions to PySpark functions (F.*) and F.col() references."""

    FUNCTION_MAP = {
        r'(?i)\bDATDIF\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*[^)]+\)': r'F.datediff(\2, \1)',
        r'(?i)\bSUBSTR\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\)': r'F.substring(\1, \2, \3)',
        r'(?i)\bSUBSTR\s*\(\s*([^,]+)\s*,\s*([^)]+)\)': r'F.substring(\1, \2, 9999)',
        r'(?i)\bUPCASE\s*\(\s*([^)]+)\)': r'F.upper(\1)',
        r'(?i)\bLOWCASE\s*\(\s*([^)]+)\)': r'F.lower(\1)',
        r'(?i)\bPROPCASE\s*\(\s*([^)]+)\)': r'F.initcap(\1)',
        r'(?i)\bSTRIP\s*\(\s*([^)]+)\)': r'F.trim(\1)',
        r'(?i)\bTRIM\s*\(\s*([^)]+)\)': r'F.trim(\1)',
        r'(?i)\bLEFT\s*\(\s*([^)]+)\)': r'F.ltrim(\1)',
        r'(?i)\bRIGHT\s*\(\s*([^)]+)\)': r'F.rtrim(\1)',
        r'(?i)\bTODAY\s*\(\s*\)': r'F.current_date()',
        r'(?i)\bDATE\s*\(\s*\)': r'F.current_date()',
        r'(?i)\bDATETIME\s*\(\s*\)': r'F.current_timestamp()',
        r'(?i)\bCOALESCE\s*\(\s*([^)]+)\)': r'F.coalesce(\1)',
        r'(?i)\bABS\s*\(\s*([^)]+)\)': r'F.abs(\1)',
        r'(?i)\bROUND\s*\(\s*([^,]+)\s*,\s*([^)]+)\)': r'F.round(\1, \2)',
        r'(?i)\bROUND\s*\(\s*([^)]+)\)': r'F.round(\1, 0)',
        r'(?i)\bCEIL\s*\(\s*([^)]+)\)': r'F.ceil(\1)',
        r'(?i)\bFLOOR\s*\(\s*([^)]+)\)': r'F.floor(\1)',
        r'(?i)\bSQRT\s*\(\s*([^)]+)\)': r'F.sqrt(\1)',
        r'(?i)\bLOG\s*\(\s*([^)]+)\)': r'F.log(\1)',
        r'(?i)\bEXP\s*\(\s*([^)]+)\)': r'F.exp(\1)',
        r'(?i)\bYEAR\s*\(\s*([^)]+)\)': r'F.year(\1)',
        r'(?i)\bMONTH\s*\(\s*([^)]+)\)': r'F.month(\1)',
        r'(?i)\bDAY\s*\(\s*([^)]+)\)': r'F.dayofmonth(\1)',
    }

    @classmethod
    def map_sql_filter(cls, expr: str) -> str:
        """Transpiles a SAS WHERE expression into a valid PySpark .filter() SQL string."""
        res = expr.strip()
        res = re.sub(r'(?<![!=<>])=(?![=])', '==', res)
        return res

    @classmethod
    def map_column_expression(cls, expr: str) -> str:
        """Transpiles a SAS assignment expression into a PySpark DataFrame Column expression."""
        res = expr.strip()

        # Handle SAS string concatenation operator || -> F.concat(...)
        if '||' in res:
            parts = [p.strip() for p in res.split('||')]
            mapped_parts = [cls.map_column_expression(p) for p in parts]
            return f"F.concat({', '.join(mapped_parts)})"

        # Handle quoted string literals
        if (res.startswith("'") and res.endswith("'")) or (res.startswith('"') and res.endswith('"')):
            return f'F.lit({res})'

        # Map missing checks
        res = re.sub(r'(?i)\b([a-zA-Z0-9_\.]+)\s+NOT\s+IS\s+MISSING\b', r'F.col("\1").isNotNull()', res)
        res = re.sub(r'(?i)\b([a-zA-Z0-9_\.]+)\s+IS\s+MISSING\b', r'F.col("\1").isNull()', res)
        res = re.sub(r'(?i)\bMISSING\s*\(\s*([a-zA-Z0-9_]+)\s*\)', r'F.col("\1").isNull()', res)

        # Map PRXMATCH regex extraction
        res = re.sub(r'(?i)\bPRXMATCH\s*\(\s*"([^"]+)"\s*,\s*([^)]+)\)', r'F.regexp_extract(\2, r"\1", 0)', res)

        # Map standard functions
        for pattern, replacement in cls.FUNCTION_MAP.items():
            res = re.sub(pattern, replacement, res)

        # Map unquoted variables to F.col("var")
        res = re.sub(r'(?<![a-zA-Z0-9_\.\"])\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?!\s*[\(\"\'])(?<!F)', r'F.col("\1")', res)
        res = re.sub(r'F\.F\.', 'F.', res)

        return res

    @classmethod
    def map_expression(cls, expr: str) -> str:
        return cls.map_column_expression(expr)
