import black
from typing import List, Optional
from sas2pyspark.models import ConvertedBlock, EGPProcessFlow, ConversionResult


class ScriptBuilder:
    """Combines converted code blocks into a standalone, production-ready PySpark script."""

    @staticmethod
    def build_script(
        blocks: List[ConvertedBlock],
        source_name: str,
        flow: Optional[EGPProcessFlow] = None
    ) -> str:
        """Assembles header, Spark initialization, converted blocks, and execution flow."""
        header_lines = [
            '"""',
            f'Auto-generated PySpark ETL Pipeline',
            f'Source: {source_name}',
            'Converted by: SAS to PySpark AI Agent',
            '"""',
            '',
            'import sys',
            'from pyspark.sql import SparkSession',
            'from pyspark.sql import functions as F',
            'from pyspark.sql import Window',
            '',
            'def main():',
            '    # Initialize SparkSession',
            '    spark = (SparkSession.builder',
            f'        .appName("PySpark_Pipeline_{source_name.replace(".", "_")}")',
            '        .getOrCreate()',
            '    )',
            '    spark.sparkContext.setLogLevel("WARN")',
            ''
        ]

        block_lines = []
        for i, b in enumerate(blocks, 1):
            block_lines.append(f"    # --- Step {i}: {b.original_block.name or b.original_block.block_type.value} ---")
            if b.conversion_notes:
                for note in b.conversion_notes:
                    block_lines.append(f"    # Note: {note}")
            if b.warnings:
                for warn in b.warnings:
                    block_lines.append(f"    # WARNING: {warn}")

            for code_line in b.pyspark_code.splitlines():
                block_lines.append(f"    {code_line}")
            block_lines.append("")

        footer_lines = [
            '    print("PySpark pipeline execution completed successfully.")',
            '    spark.stop()',
            '',
            'if __name__ == "__main__":',
            '    main()'
        ]

        full_code = "\n".join(header_lines + block_lines + footer_lines)

        # Attempt to format code using Black formatter
        try:
            full_code = black.format_str(full_code, mode=black.FileMode())
        except Exception:
            pass

        return full_code
