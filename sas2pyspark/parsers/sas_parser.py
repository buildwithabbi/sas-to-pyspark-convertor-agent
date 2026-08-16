import re
from typing import List, Tuple, Optional
from sas2pyspark.models import SASCodeBlock, BlockType


class SASParser:
    """Parses raw SAS code into structured SASCodeBlocks with extracted metadata."""

    def __init__(self):
        # Patterns for SAS blocks
        self.block_split_pattern = re.compile(
            r'(?i)(^\s*(?:DATA\b|PROC\b|%MACRO\b|%LET\b|LIBNAME\b))', re.MULTILINE
        )

    def parse_script(self, sas_code: str) -> List[SASCodeBlock]:
        """Splits SAS script into individual logical blocks and extracts dataset dependencies."""
        cleaned_code = self._strip_comments(sas_code)
        tokens = self._tokenize_blocks(cleaned_code)

        blocks: List[SASCodeBlock] = []
        for idx, (block_str, line_num) in enumerate(tokens):
            block_str = block_str.strip()
            if not block_str:
                continue

            block_type = self._identify_block_type(block_str)
            inputs, outputs = self._extract_datasets(block_str, block_type)
            name = self._extract_block_name(block_str, block_type)

            block = SASCodeBlock(
                id=f"block_{idx + 1}",
                block_type=block_type,
                name=name,
                input_datasets=inputs,
                output_datasets=outputs,
                raw_code=block_str,
                line_number=line_num,
            )
            blocks.append(block)

        return blocks

    def _strip_comments(self, code: str) -> str:
        """Strips /* ... */ and * ... ; comments and EGP log prefixes while preserving line breaks."""
        # Strip EGP log line prefixes (e.g. 's 22 ', 'n NOTE: ', 't12 ')
        code = re.sub(r'^[snt]\d*\s+(?=\S)', '', code, flags=re.MULTILINE)
        code = re.sub(r'^n NOTE:.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'^\d+\s+(?=[A-Za-z%*])', '', code, flags=re.MULTILINE)

        # Block comments /* ... */
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        # Single line SAS comments * ... ;
        lines = code.splitlines()
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('*') and ';' in stripped:
                cleaned_lines.append('')
            else:
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    def _tokenize_blocks(self, code: str) -> List[Tuple[str, int]]:
        """Splits code by statements terminated with RUN;, QUIT;, or %MEND;."""
        statements = re.split(r'(?i)(?<=\bRUN;)|(?<=\bQUIT;)|(?<=%MEND;)|(?<=;)', code)
        blocks = []
        line_counter = 1
        current_block = ""
        block_start_line = 1

        for stmt in statements:
            if not current_block:
                block_start_line = line_counter

            current_block += stmt
            line_counter += stmt.count('\n')

            # Check if block is complete
            if re.search(r'(?i)\b(RUN|QUIT);|%MEND\b', stmt) or (
                re.match(r'(?i)^\s*(%LET|LIBNAME)\b', current_block.strip()) and stmt.strip().endswith(';')
            ):
                blocks.append((current_block, block_start_line))
                current_block = ""

        if current_block.strip():
            blocks.append((current_block, block_start_line))

        return blocks

    def _identify_block_type(self, block: str) -> BlockType:
        block_upper = block.strip().upper()
        if block_upper.startswith("DATA"):
            return BlockType.DATA_STEP
        elif block_upper.startswith("PROC SQL"):
            return BlockType.PROC_SQL
        elif block_upper.startswith("PROC SORT"):
            return BlockType.PROC_SORT
        elif block_upper.startswith("PROC TRANSPOSE"):
            return BlockType.PROC_TRANSPOSE
        elif block_upper.startswith("PROC SUMMARY"):
            return BlockType.PROC_SUMMARY
        elif block_upper.startswith("PROC MEANS"):
            return BlockType.PROC_MEANS
        elif block_upper.startswith("PROC FREQ"):
            return BlockType.PROC_FREQ
        elif block_upper.startswith("PROC IMPORT"):
            return BlockType.PROC_IMPORT
        elif block_upper.startswith("PROC EXPORT"):
            return BlockType.PROC_EXPORT
        elif block_upper.startswith("PROC FORMAT") or "<CREATEIMPORTEDFORMATSTATE" in block_upper:
            return BlockType.PROC_FORMAT
        elif block_upper.startswith("PROC"):
            return BlockType.PROC_OTHER
        elif block_upper.startswith("%MACRO"):
            return BlockType.MACRO_DEF
        elif block_upper.startswith("%LET"):
            return BlockType.LET_STATEMENT
        elif block_upper.startswith("LIBNAME"):
            return BlockType.LIBNAME
        elif block_upper.startswith("%"):
            return BlockType.MACRO_CALL
        return BlockType.UNKNOWN

    def _extract_datasets(self, block: str, block_type: BlockType) -> Tuple[List[str], List[str]]:
        inputs = []
        outputs = []

        if block_type == BlockType.DATA_STEP:
            # DATA output_ds1 output_ds2;
            data_match = re.search(r'(?i)\bDATA\s+([^;]+);', block)
            if data_match:
                raw_outs = data_match.group(1).strip().split()
                for out in raw_outs:
                    cleaned = re.sub(r'\(.*?\)', '', out).strip()
                    if cleaned and not cleaned.startswith('('):
                        outputs.append(cleaned)

            # SET input_ds; MERGE ds1 ds2;
            set_matches = re.findall(r'(?i)\b(?:SET|MERGE)\s+([^;]+);', block)
            for sm in set_matches:
                raw_ins = sm.strip().split()
                for inp in raw_ins:
                    cleaned = re.sub(r'\(.*?\)', '', inp).strip()
                    if cleaned and not cleaned.upper() in ('KEY=', 'NOBS=', 'END='):
                        inputs.append(cleaned)

        elif block_type == BlockType.PROC_SQL:
            # FROM table_name / JOIN table_name
            from_matches = re.findall(r'(?i)\b(?:FROM|JOIN)\s+([a-zA-Z0-9_\.]+)', block)
            inputs.extend(from_matches)
            # CREATE TABLE output_ds AS
            create_match = re.search(r'(?i)\bCREATE\s+TABLE\s+([a-zA-Z0-9_\.]+)', block)
            if create_match:
                outputs.append(create_match.group(1))

        elif block_type in (BlockType.PROC_SORT, BlockType.PROC_TRANSPOSE, BlockType.PROC_SUMMARY, BlockType.PROC_MEANS, BlockType.PROC_FREQ):
            data_m = re.search(r'(?i)\bDATA\s*=\s*([a-zA-Z0-9_\.]+)', block)
            if data_m:
                inputs.append(data_m.group(1))
            out_m = re.search(r'(?i)\bOUT\s*=\s*([a-zA-Z0-9_\.]+)', block)
            if out_m:
                outputs.append(out_m.group(1))

        return list(dict.fromkeys(inputs)), list(dict.fromkeys(outputs))

    def _extract_block_name(self, block: str, block_type: BlockType) -> Optional[str]:
        if block_type == BlockType.DATA_STEP:
            m = re.search(r'(?i)\bDATA\s+([a-zA-Z0-9_\.]+)', block)
            return f"data_step_{m.group(1)}" if m else "data_step"
        elif block_type == BlockType.PROC_SQL:
            m = re.search(r'(?i)\bCREATE\s+TABLE\s+([a-zA-Z0-9_\.]+)', block)
            return f"proc_sql_{m.group(1)}" if m else "proc_sql"
        elif block_type.value.startswith("PROC_"):
            return block_type.value.lower()
        return None
