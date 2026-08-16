import json
from typing import List, Dict, Any, Optional
from sas2pyspark.models import ConvertedBlock, EGPProcessFlow


class NotebookBuilder:
    """Builds a Jupyter Notebook (.ipynb) from converted SAS code blocks."""

    @staticmethod
    def build_notebook(
        blocks: List[ConvertedBlock],
        source_name: str,
        flow: Optional[EGPProcessFlow] = None
    ) -> Dict[str, Any]:
        cells = []

        # Title Cell
        title_markdown = [
            f"# PySpark ETL Pipeline: {source_name}\n",
            "Auto-converted from SAS using **SAS to PySpark AI Agent**.\n",
            "---\n"
        ]
        if flow:
            title_markdown.append(f"**Process Flow:** `{flow.name}` ({len(flow.nodes)} tasks)\n")

        cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": title_markdown
        })

        # Spark Setup Cell
        spark_setup_code = [
            "# Initialize PySpark Session\n",
            "from pyspark.sql import SparkSession\n",
            "from pyspark.sql import functions as F\n",
            "from pyspark.sql import Window\n\n",
            "spark = SparkSession.builder \\\n",
            f'    .appName("Notebook_{source_name.replace(".", "_")}") \\\n',
            "    .getOrCreate()\n\n",
            'print(f"Spark Session active: {spark.version}")'
        ]
        cells.append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": spark_setup_code
        })

        # Block Cells
        for idx, b in enumerate(blocks, 1):
            md_lines = [
                f"### Step {idx}: {b.original_block.name or b.original_block.block_type.value}\n",
                f"**Block Type:** `{b.original_block.block_type.value}` | **Confidence:** `{int(b.confidence_score * 100)}%`\n"
            ]

            if b.conversion_notes:
                md_lines.append("**Notes:**\n" + "".join([f"- {n}\n" for n in b.conversion_notes]))

            if b.warnings:
                md_lines.append("**Warnings:**\n" + "".join([f"- ⚠️ {w}\n" for w in b.warnings]))

            md_lines.append("\n<details><summary>Original SAS Code</summary>\n\n```sas\n" + b.original_block.raw_code + "\n```\n</details>")

            cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": md_lines
            })

            cells.append({
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [line + "\n" for line in b.pyspark_code.splitlines()]
            })

        notebook_json = {
            "cells": cells,
            "metadata": {
                "language_info": {"name": "python", "version": "3.12"},
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}
            },
            "nbformat": 4,
            "nbformat_minor": 2
        }

        return notebook_json
