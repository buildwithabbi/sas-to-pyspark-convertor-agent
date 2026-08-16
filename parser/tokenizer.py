import re
from typing import List, Tuple


class SASTokenizer:
    """Tokenizes SAS scripts into clean statements and blocks."""

    def tokenize(self, sas_code: str) -> List[Tuple[str, int]]:
        cleaned = self._strip_comments(sas_code)
        statements = re.split(r'(?i)(?<=\bRUN;)|(?<=\bQUIT;)|(?<=%MEND;)|(?<=;)', cleaned)

        blocks = []
        line_counter = 1
        current_block = ""
        block_start = 1

        for stmt in statements:
            if not current_block:
                block_start = line_counter

            current_block += stmt
            line_counter += stmt.count('\n')

            if re.search(r'(?i)\b(RUN|QUIT);|%MEND\b', stmt) or (
                re.match(r'(?i)^\s*(%LET|LIBNAME)\b', current_block.strip()) and stmt.strip().endswith(';')
            ):
                blocks.append((current_block.strip(), block_start))
                current_block = ""

        if current_block.strip():
            blocks.append((current_block.strip(), block_start))

        return [(b, l) for b, l in blocks if b]

    def _strip_comments(self, code: str) -> str:
        # Strip line numbers and log prefixes
        code = re.sub(r'^[snt]\d*\s+(?=\S)', '', code, flags=re.MULTILINE)
        code = re.sub(r'^n NOTE:.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'^\d+\s+(?=[A-Za-z%*])', '', code, flags=re.MULTILINE)

        # Strip block comments /* ... */
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

        # Strip single line comments * ... ;
        lines = code.splitlines()
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('*') and ';' in stripped:
                cleaned_lines.append('')
            else:
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)
