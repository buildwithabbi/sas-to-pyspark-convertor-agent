import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any
from sas2pyspark.models import SASCodeBlock, ConvertedBlock


class ProcFormatTranspiler:
    """Transpiles SAS PROC FORMAT and EGP <CreateImportedFormatState> to PySpark dictionary mappings and F.when() functions."""

    def transpile(self, block: SASCodeBlock) -> ConvertedBlock:
        raw = block.raw_code
        notes = []
        warnings = []

        # 1. Handle EGP <CreateImportedFormatState> XML format definition
        if "<CreateImportedFormatState" in raw:
            return self._transpile_egp_format_xml(block, raw)

        # 2. Handle standard SAS PROC FORMAT; VALUE $fmt ...; RUN;
        format_name_match = re.search(r'(?i)VALUE\s+\$?([a-zA-Z0-9_]+)', raw)
        fmt_name = format_name_match.group(1) if format_name_match else "custom_format"

        pairs = re.findall(r"([0-9a-zA-Z_\.\'\"]+)\s*=\s*[\'\"]([^\'\"]+)[\'\"]", raw)
        other_match = re.search(r"(?i)\bOTHER\s*=\s*[\'\"]([^\'\"]+)[\'\"]", raw)
        default_val = other_match.group(1) if other_match else "Unknown"

        lines = [
            f"# --- PROC FORMAT Mapping Function for '{fmt_name}' ---",
            f"{fmt_name}_map = {{"
        ]

        for k, v in pairs:
            if k.upper() != "OTHER":
                lines.append(f"    {k}: \"{v}\",")
        lines.append("}")
        lines.append("")
        lines.append(f"def apply_{fmt_name}_format(col_expr):")

        when_lines = []
        for k, v in pairs:
            if k.upper() != "OTHER":
                when_lines.append(f".when(col_expr == {k}, \"{v}\")")

        if when_lines:
            when_chain = "\n        ".join(when_lines)
            lines.append(f"    return (\n        F{when_chain}\n        .otherwise(\"{default_val}\")\n    )")
        else:
            lines.append(f"    return F.lit(\"{default_val}\")")

        pyspark_code = "\n".join(lines)
        notes.append(f"Transpiled PROC FORMAT '{fmt_name}' to PySpark apply_{fmt_name}_format() mapping function")

        return ConvertedBlock(
            original_block=block,
            pyspark_code=pyspark_code,
            confidence_score=0.95,
            conversion_notes=notes,
            warnings=warnings,
            used_llm=False
        )

    def _transpile_egp_format_xml(self, block: SASCodeBlock, xml_str: str) -> ConvertedBlock:
        fmt_name = "custom_format"
        default_val = "Unknown"
        try:
            root = ET.fromstring(xml_str)
            fmt_elem = root.find("FormatName")
            if fmt_elem is not None and fmt_elem.text:
                fmt_name = fmt_elem.text

            def_elem = root.find("DefaultLabel")
            if def_elem is not None and def_elem.text:
                default_val = def_elem.text
        except Exception:
            pass

        lines = [
            f"# --- EGP Imported Format Definition for '{fmt_name}' ---",
            f"def apply_{fmt_name}_format(col_expr):",
            f"    # Maps input column using {fmt_name} format specification",
            f"    return F.when(col_expr.isNotNull(), col_expr.cast(\"string\")).otherwise(\"{default_val}\")"
        ]

        pyspark_code = "\n".join(lines)

        return ConvertedBlock(
            original_block=block,
            pyspark_code=pyspark_code,
            confidence_score=0.90,
            conversion_notes=[f"Transpiled EGP <CreateImportedFormatState> '{fmt_name}' to PySpark mapping function"],
            warnings=[],
            used_llm=False
        )
