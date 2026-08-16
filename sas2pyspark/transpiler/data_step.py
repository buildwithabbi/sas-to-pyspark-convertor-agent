import re
from typing import List, Tuple
from sas2pyspark.models import SASCodeBlock, ConvertedBlock
from sas2pyspark.transpiler.functions import SASFunctionMapper


class DataStepTranspiler:
    """Transpiles SAS DATA step code blocks to PySpark DataFrame transformations and MERGE joins."""

    def __init__(self):
        self.fn_mapper = SASFunctionMapper()

    def transpile(self, block: SASCodeBlock) -> ConvertedBlock:
        raw = block.raw_code
        out_ds = block.output_datasets[0] if block.output_datasets else "output_df"
        out_df = out_ds.replace('.', '_')

        notes = []
        warnings = []
        lines = []

        # 1. Check for MERGE statement
        merge_match = re.search(r'(?i)\bMERGE\s+([^;]+);', raw)
        by_match = re.search(r'(?i)\bBY\s+([^;]+);', raw)

        if merge_match and len(block.input_datasets) >= 2:
            by_keys = [k.strip() for k in by_match.group(1).split()] if by_match else []
            keys_repr = ", ".join([f'"{k}"' for k in by_keys])

            ds1 = block.input_datasets[0].replace('.', '_')
            ds2 = block.input_datasets[1].replace('.', '_')

            # Determine join type from IF a AND b or default full_outer
            join_type = "full_outer"
            if re.search(r'(?i)\bIF\s+[a-z]\s+AND\s+[a-z]', raw):
                join_type = "inner"
                notes.append("Detected IF a AND b clause: set join_type='inner'")
            elif re.search(r'(?i)\bIF\s+[a-z]\b', raw):
                join_type = "left"
                notes.append("Detected IF a clause: set join_type='left'")

            notes.append(f"Transpiled SAS MERGE BY [{', '.join(by_keys)}] into PySpark {join_type} join")

            lines.append(f"{out_df} = {ds1}.join({ds2}, on=[{keys_repr}], how=\"{join_type}\")")

            # Perform remaining column operations or filters
            statements = [s.strip() for s in raw.split(';') if s.strip()]
            for stmt in statements:
                stmt_upper = stmt.upper()
                if stmt_upper.startswith('WHERE'):
                    where_expr = stmt[5:].strip()
                    spark_expr = self.fn_mapper.map_sql_filter(where_expr)
                    lines.append(f"{out_df} = {out_df}.filter(\"{spark_expr}\")")

            lines.append(f"{out_df}.createOrReplaceTempView(\"{out_df}\")")
            pyspark_code = "\n".join(lines)

            return ConvertedBlock(
                original_block=block,
                pyspark_code=pyspark_code,
                confidence_score=0.95,
                conversion_notes=notes,
                warnings=warnings,
                used_llm=False
            )

        # Standard DATA step transformation
        in_ds = block.input_datasets[0] if block.input_datasets else "input_df"
        in_df = in_ds.replace('.', '_')

        has_first_last = bool(re.search(r'(?i)\b(?:FIRST|LAST)\.[a-zA-Z0-9_]+', raw))
        has_retain = bool(re.search(r'(?i)\bRETAIN\b', raw))

        if has_first_last or has_retain:
            notes.append("Detected Window-based SAS logic (FIRST./LAST./RETAIN)")

        lines.append(f"{out_df} = (")
        lines.append(f"    {in_df}")

        statements = [s.strip() for s in raw.split(';') if s.strip()]

        for stmt in statements:
            stmt_upper = stmt.upper()
            if stmt_upper.startswith('DATA') or stmt_upper.startswith('SET') or stmt_upper.startswith('RUN'):
                continue
            elif stmt_upper.startswith('WHERE'):
                where_expr = stmt[5:].strip()
                spark_expr = self.fn_mapper.map_sql_filter(where_expr)
                lines.append(f"    .filter(\"{spark_expr}\")")
                notes.append(f"Mapped WHERE clause: {where_expr}")
            elif stmt_upper.startswith('KEEP'):
                cols = stmt[4:].strip().split()
                cols_repr = ", ".join([f'"{c}"' for c in cols])
                lines.append(f"    .select({cols_repr})")
                notes.append("Mapped KEEP statement to .select()")
            elif stmt_upper.startswith('DROP'):
                cols = stmt[4:].strip().split()
                cols_repr = ", ".join([f'"{c}"' for c in cols])
                lines.append(f"    .drop({cols_repr})")
                notes.append("Mapped DROP statement to .drop()")
            elif stmt_upper.startswith('IF') and 'THEN' in stmt_upper:
                if_match = re.search(r'(?i)IF\s+(.+?)\s+THEN\s+([a-zA-Z0-9_]+)\s*=\s*(.+)', stmt)
                if if_match:
                    cond = if_match.group(1).strip()
                    target_var = if_match.group(2).strip()
                    val = if_match.group(3).strip()

                    spark_cond = self.fn_mapper.map_column_expression(cond)
                    spark_val = self.fn_mapper.map_column_expression(val)

                    lines.append(
                        f"    .withColumn(\"{target_var}\", F.when({spark_cond}, {spark_val}).otherwise(F.col(\"{target_var}\")))"
                    )
                    notes.append(f"Mapped IF-THEN conditional assignment to {target_var}")
            elif '=' in stmt and not stmt_upper.startswith('BY') and not stmt_upper.startswith('RETAIN'):
                assign_match = re.search(r'([a-zA-Z0-9_]+)\s*=\s*(.+)', stmt)
                if assign_match:
                    target_var = assign_match.group(1).strip()
                    val_expr = assign_match.group(2).strip()
                    spark_val = self.fn_mapper.map_column_expression(val_expr)
                    lines.append(f"    .withColumn(\"{target_var}\", {spark_val})")
                    notes.append(f"Mapped assignment for {target_var}")

        lines.append(")")
        lines.append(f"{out_df}.createOrReplaceTempView(\"{out_df}\")")

        pyspark_code = "\n".join(lines)

        return ConvertedBlock(
            original_block=block,
            pyspark_code=pyspark_code,
            confidence_score=0.90 if not warnings else 0.65,
            conversion_notes=notes,
            warnings=warnings,
            used_llm=False
        )
