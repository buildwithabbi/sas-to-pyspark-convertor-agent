import re
from typing import Dict
from sas2pyspark.models import SASCodeBlock, ConvertedBlock


class MacroTranspiler:
    """Handles SAS macro variables (%LET) and macro expansions."""

    def __init__(self):
        self.macro_vars: Dict[str, str] = {}

    def transpile_let(self, block: SASCodeBlock) -> ConvertedBlock:
        raw = block.raw_code
        match = re.search(r'(?i)%LET\s+([a-zA-Z0-9_]+)\s*=\s*([^;]+);', raw)
        if match:
            var_name = match.group(1).strip()
            var_val = match.group(2).strip().strip('"\'')
            self.macro_vars[var_name] = var_val

            code = f'# SAS Macro Variable\n{var_name} = "{var_val}"'
            return ConvertedBlock(
                original_block=block,
                pyspark_code=code,
                confidence_score=1.0,
                conversion_notes=[f"Defined macro variable {var_name}"],
                used_llm=False
            )
        else:
            return ConvertedBlock(
                original_block=block,
                pyspark_code=f"# {raw}",
                confidence_score=0.8,
                used_llm=False
            )

    def substitute_macro_vars(self, code: str) -> str:
        """Replaces &var_name with string value in code."""
        result = code
        for var_name, var_val in self.macro_vars.items():
            pattern = re.compile(rf'&{var_name}\.?', re.IGNORECASE)
            result = pattern.sub(var_val, result)
        return result
