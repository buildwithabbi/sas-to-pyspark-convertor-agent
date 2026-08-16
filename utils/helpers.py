import re

def clean_sas_table_name(table_name: str) -> str:
    """Normalizes SAS WORK.table_name to valid PySpark identifier work_table_name."""
    if not table_name:
        return "table"
    cleaned = table_name.strip().replace('.', '_')
    return re.sub(r'[^a-zA-Z0-9_]', '', cleaned)

def clean_code_block(code: str) -> str:
    """Strips markdown python code block indicators."""
    res = re.sub(r'^```python\s*', '', code, flags=re.MULTILINE)
    res = re.sub(r'^```\s*$', '', res, flags=re.MULTILINE)
    return res.strip()
