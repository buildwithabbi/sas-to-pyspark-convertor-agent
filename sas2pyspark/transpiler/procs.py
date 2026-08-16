import re
from typing import Tuple, List
from sas2pyspark.models import SASCodeBlock, ConvertedBlock, BlockType


class ProcTranspiler:
    """Transpiles SAS PROCs (SORT, TRANSPOSE, SUMMARY, MEANS, FREQ, IMPORT, EXPORT) to PySpark."""

    def transpile(self, block: SASCodeBlock) -> ConvertedBlock:
        b_type = block.block_type
        raw = block.raw_code
        notes = []
        warnings = []

        if b_type == BlockType.PROC_SORT:
            code = self._transpile_sort(block, notes)
        elif b_type == BlockType.PROC_TRANSPOSE:
            code = self._transpile_transpose(block, notes)
        elif b_type in (BlockType.PROC_SUMMARY, BlockType.PROC_MEANS):
            code = self._transpile_summary(block, notes)
        elif b_type == BlockType.PROC_FREQ:
            code = self._transpile_freq(block, notes)
        elif b_type == BlockType.PROC_IMPORT:
            code = self._transpile_import(block, notes)
        elif b_type == BlockType.PROC_EXPORT:
            code = self._transpile_export(block, notes)
        elif b_type == BlockType.PROC_FORMAT:
            from sas2pyspark.transpiler.format_transpiler import ProcFormatTranspiler
            return ProcFormatTranspiler().transpile(block)
        else:
            code = f"# TODO: Manual translation required for PROC {block.name}\n# SAS Code:\n# {raw.replace('\n', '\n# ')}"
            warnings.append(f"PROC {block.name} is not fully supported in rule-based transpiler.")

        return ConvertedBlock(
            original_block=block,
            pyspark_code=code,
            confidence_score=0.95 if not warnings else 0.6,
            conversion_notes=notes,
            warnings=warnings,
            used_llm=False
        )

    def _transpile_sort(self, block: SASCodeBlock, notes: List[str]) -> str:
        raw = block.raw_code
        in_ds = block.input_datasets[0] if block.input_datasets else "input_df"
        out_ds = block.output_datasets[0] if block.output_datasets else in_ds

        in_df = in_ds.replace('.', '_')
        out_df = out_ds.replace('.', '_')

        # Extract BY columns
        by_match = re.search(r'(?i)\bBY\s+([^;]+);', raw)
        sort_cols = []
        if by_match:
            by_cols_raw = by_match.group(1).split()
            descending = False
            for token in by_cols_raw:
                if token.upper() == 'DESCENDING':
                    descending = True
                else:
                    col_name = token.strip()
                    if descending:
                        sort_cols.append(f'F.col("{col_name}").desc()')
                        descending = False
                    else:
                        sort_cols.append(f'F.col("{col_name}").asc()')

        sort_str = ", ".join(sort_cols) if sort_cols else 'F.col("id")'
        # Check NODUPKEY / NODUP
        nodup = bool(re.search(r'(?i)\bNODUPKEY\b|\bNODUP\b', raw))

        lines = []
        if in_df != out_df:
            lines.append(f"{out_df} = {in_df}.sort({sort_str})")
        else:
            lines.append(f"{out_df} = {out_df}.sort({sort_str})")

        if nodup:
            cols_only = [c.split('"')[1] for c in sort_cols if '"' in c]
            if cols_only:
                cols_repr = ", ".join([f'"{c}"' for c in cols_only])
                lines.append(f"{out_df} = {out_df}.dropDuplicates([{cols_repr}])")
            else:
                lines.append(f"{out_df} = {out_df}.dropDuplicates()")
            notes.append("Converted NODUPKEY to dropDuplicates()")

        lines.append(f"{out_df}.createOrReplaceTempView(\"{out_df}\")")
        notes.append(f"Transpiled PROC SORT by [{sort_str}]")
        return "\n".join(lines)

    def _transpile_transpose(self, block: SASCodeBlock, notes: List[str]) -> str:
        raw = block.raw_code
        in_ds = block.input_datasets[0] if block.input_datasets else "input_df"
        out_ds = block.output_datasets[0] if block.output_datasets else "transposed_df"
        in_df = in_ds.replace('.', '_')
        out_df = out_ds.replace('.', '_')

        by_m = re.search(r'(?i)\bBY\s+([^;]+);', raw)
        var_m = re.search(r'(?i)\bVAR\s+([^;]+);', raw)
        id_m = re.search(r'(?i)\bID\s+([^;]+);', raw)

        by_cols = by_m.group(1).strip().split() if by_m else []
        var_cols = var_m.group(1).strip().split() if var_m else []
        id_cols = id_m.group(1).strip().split() if id_m else []

        by_repr = ", ".join([f'"{c}"' for c in by_cols])
        var_col = var_cols[0] if var_cols else "value"
        pivot_col = id_cols[0] if id_cols else "variable"

        lines = [
            f"{out_df} = ({in_df}",
            f"    .groupBy({by_repr})",
            f"    .pivot(\"{pivot_col}\")",
            f"    .agg(F.first(\"{var_col}\"))",
            f")",
            f"{out_df}.createOrReplaceTempView(\"{out_df}\")"
        ]
        notes.append("Transpiled PROC TRANSPOSE to PySpark groupBy().pivot()")
        return "\n".join(lines)

    def _transpile_summary(self, block: SASCodeBlock, notes: List[str]) -> str:
        raw = block.raw_code
        in_ds = block.input_datasets[0] if block.input_datasets else "input_df"
        out_ds = block.output_datasets[0] if block.output_datasets else "summary_df"
        in_df = in_ds.replace('.', '_')
        out_df = out_ds.replace('.', '_')

        class_m = re.search(r'(?i)\bCLASS\s+([^;]+);', raw)
        var_m = re.search(r'(?i)\bVAR\s+([^;]+);', raw)

        class_cols = class_m.group(1).strip().split() if class_m else []
        var_cols = var_m.group(1).strip().split() if var_m else []

        class_repr = ", ".join([f'"{c}"' for c in class_cols])
        aggs = []
        for v in var_cols:
            aggs.append(f'F.sum("{v}").alias("{v}_sum")')
            aggs.append(f'F.avg("{v}").alias("{v}_mean")')

        agg_repr = ",\n        ".join(aggs) if aggs else 'F.count("*").alias("record_count")'

        if class_cols:
            lines = [
                f"{out_df} = ({in_df}",
                f"    .groupBy({class_repr})",
                f"    .agg(\n        {agg_repr}\n    )",
                f")",
                f"{out_df}.createOrReplaceTempView(\"{out_df}\")"
            ]
        else:
            lines = [
                f"{out_df} = ({in_df}",
                f"    .agg(\n        {agg_repr}\n    )",
                f")",
                f"{out_df}.createOrReplaceTempView(\"{out_df}\")"
            ]
        notes.append("Transpiled PROC SUMMARY/MEANS to PySpark DataFrame aggregation")
        return "\n".join(lines)

    def _transpile_freq(self, block: SASCodeBlock, notes: List[str]) -> str:
        raw = block.raw_code
        in_ds = block.input_datasets[0] if block.input_datasets else "input_df"
        out_ds = block.output_datasets[0] if block.output_datasets else "freq_df"
        in_df = in_ds.replace('.', '_')
        out_df = out_ds.replace('.', '_')

        tables_m = re.search(r'(?i)\bTABLES?\s+([^;/]+)', raw)
        tbl_cols = tables_m.group(1).strip().replace('*', ' ').split() if tables_m else []

        cols_repr = ", ".join([f'"{c}"' for c in tbl_cols]) if tbl_cols else '"category"'

        lines = [
            f"{out_df} = ({in_df}",
            f"    .groupBy({cols_repr})",
            f"    .agg(F.count(\"*\").alias(\"count\"))",
            f")",
            f"{out_df}.createOrReplaceTempView(\"{out_df}\")"
        ]
        notes.append("Transpiled PROC FREQ to PySpark frequency count aggregation")
        return "\n".join(lines)

    def _transpile_import(self, block: SASCodeBlock, notes: List[str]) -> str:
        raw = block.raw_code
        out_ds = block.output_datasets[0] if block.output_datasets else "imported_df"
        out_df = out_ds.replace('.', '_')

        file_m = re.search(r'(?i)\bDATAFILE\s*=\s*["\']?([^"\'\s;]+)["\']?', raw)
        dbms_m = re.search(r'(?i)\bDBMS\s*=\s*([a-zA-Z0-9]+)', raw)

        filepath = file_m.group(1) if file_m else "path/to/file.csv"
        dbms = dbms_m.group(1).upper() if dbms_m else "CSV"

        if dbms in ('CSV', 'DLM', 'TXT'):
            lines = [
                f"{out_df} = (spark.read",
                f"    .option(\"header\", \"true\")",
                f"    .option(\"inferSchema\", \"true\")",
                f"    .csv(\"{filepath}\")",
                f")",
                f"{out_df}.createOrReplaceTempView(\"{out_df}\")"
            ]
        elif dbms in ('EXCEL', 'XLSX'):
            lines = [
                f"{out_df} = (spark.read",
                f"    .format(\"com.crealytics.spark.excel\")",
                f"    .option(\"header\", \"true\")",
                f"    .load(\"{filepath}\")",
                f")",
                f"{out_df}.createOrReplaceTempView(\"{out_df}\")"
            ]
        else:
            lines = [
                f"{out_df} = spark.read.load(\"{filepath}\")",
                f"{out_df}.createOrReplaceTempView(\"{out_df}\")"
            ]
        notes.append(f"Transpiled PROC IMPORT DBMS={dbms}")
        return "\n".join(lines)

    def _transpile_export(self, block: SASCodeBlock, notes: List[str]) -> str:
        raw = block.raw_code
        in_ds = block.input_datasets[0] if block.input_datasets else "input_df"
        in_df = in_ds.replace('.', '_')

        file_m = re.search(r'(?i)\bOUTFILE\s*=\s*["\']?([^"\'\s;]+)["\']?', raw)
        filepath = file_m.group(1) if file_m else "path/to/output.csv"

        lines = [
            f"({in_df}.write",
            f"    .option(\"header\", \"true\")",
            f"    .mode(\"overwrite\")",
            f"    .csv(\"{filepath}\")",
            f")"
        ]
        notes.append("Transpiled PROC EXPORT to spark write.csv()")
        return "\n".join(lines)
