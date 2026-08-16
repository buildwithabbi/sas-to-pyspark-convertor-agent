#!/usr/bin/env python3
"""
SAS to PySpark Multi-Agent Orchestrator (app.py)
Orchestrates Agent 1 (Analyzer) -> Agent 2 (Knowledge) -> Agent 3 (Translator) 
-> Agent 4 (Optimizer) -> Agent 5 (Validator) -> Agent 6 (Documentation)
"""

import sys
import json
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agents import (
    SASAnalyzerAgent,
    SASKnowledgeAgent,
    SASTranslatorAgent,
    PySparkOptimizerAgent,
    PySparkValidatorAgent,
    DocumentationAgent
)
from sas2pyspark.generator import ScriptBuilder, NotebookBuilder

cli_app = typer.Typer(name="sas_to_spark_agent", help="🚀 Multi-Agent System for converting SAS/EGP to PySpark.")
console = Console()


@cli_app.command()
def run(
    input_path: str = typer.Argument(..., help="Path to input SAS (.sas) or EGP (.egp) file"),
    output_dir: str = typer.Option("./output", "--out", "-o", help="Output directory"),
    dump_ir: bool = typer.Option(True, "--dump-ir", help="Dump intermediate AST IR JSON"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Spin up local PySpark session for schema & execution validation"),
):
    """Runs the 6-Agent pipeline to analyze, translate, optimize, validate, and document the SAS conversion."""
    path = Path(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    console.print(Panel(f"[bold gold1]Starting Multi-Agent SAS -> PySpark Pipeline for: {path.name}[/bold gold1]"))

    # Agent 1: Analyzer
    console.print("🤖 [bold cyan]Agent 1 (SAS Analyzer):[/bold cyan] Extracting SAS AST & Flow IR...")
    analyzer = SASAnalyzerAgent()
    ir_data = analyzer.analyze(str(path))

    if dump_ir:
        ir_file = out_dir / f"{path.stem}_intermediate_ir.json"
        ir_file.write_text(json.dumps(ir_data, indent=2), encoding='utf-8')
        console.print(f"  └─ Exported Intermediate IR: [bold yellow]{ir_file}[/bold yellow]")

    # Agent 2: Knowledge Base
    console.print("🤖 [bold cyan]Agent 2 (SAS Knowledge Agent):[/bold cyan] Querying SAS-to-PySpark construct mappings...")
    knowledge = SASKnowledgeAgent()
    mappings = knowledge.get_all_mappings()
    console.print(f"  └─ Loaded {len(mappings)} construct mapping rules")

    # Agent 3: Translator
    console.print("🤖 [bold cyan]Agent 3 (Translator):[/bold cyan] Translating SAS code blocks to PySpark...")
    translator = SASTranslatorAgent()
    translated_steps = translator.translate_all(ir_data)

    # Agent 4: Optimizer
    console.print("🤖 [bold cyan]Agent 4 (Optimizer):[/bold cyan] Applying PySpark performance optimizations...")
    optimizer = PySparkOptimizerAgent()
    optimized_steps = optimizer.optimize_steps(translated_steps)

    # Agent 5: Validator
    console.print("🤖 [bold cyan]Agent 5 (Validator):[/bold cyan] Running AST compilation & schema integrity checks...")
    validator = PySparkValidatorAgent()
    validated_steps = validator.validate_all(optimized_steps)

    # Agent 6: Documentation
    console.print("🤖 [bold cyan]Agent 6 (Documentation Agent):[/bold cyan] Building data lineage graph and migration report...")
    doc_agent = DocumentationAgent()
    lineage_doc = doc_agent.generate_documentation(path.name, validated_steps)
    doc_file = out_dir / f"{path.stem}_migration_lineage.md"
    doc_file.write_text(lineage_doc, encoding='utf-8')
    console.print(f"  └─ Generated Documentation: [bold green]{doc_file}[/bold green]")

    # Generate Final Executable PySpark Script & Notebook
    converted_blocks = []
    for s in validated_steps:
        from sas2pyspark.models import SASCodeBlock, ConvertedBlock, BlockType
        try:
            bt = BlockType(s["block_type"])
        except ValueError:
            bt = BlockType.UNKNOWN

        block = SASCodeBlock(
            id=s["step_id"],
            block_type=bt,
            name=s["name"],
            raw_code=s.get("pyspark_code", "")
        )
        cb = ConvertedBlock(
            original_block=block,
            pyspark_code=s["pyspark_code"],
            confidence_score=s["confidence_score"],
            conversion_notes=s.get("notes", []),
            warnings=s.get("warnings", []),
            used_llm=False
        )
        converted_blocks.append(cb)

    script_code = ScriptBuilder.build_script(converted_blocks, path.name)
    script_file = out_dir / f"{path.stem}_converted.py"
    script_file.write_text(script_code, encoding='utf-8')
    console.print(f"  └─ Generated Final PySpark Script: [bold green]{script_file}[/bold green]")

    notebook_json = NotebookBuilder.build_notebook(converted_blocks, path.name)
    notebook_file = out_dir / f"{path.stem}_converted.ipynb"
    notebook_file.write_text(json.dumps(notebook_json, indent=2), encoding='utf-8')
    console.print(f"  └─ Generated Final Notebook: [bold green]{notebook_file}[/bold green]")

    if dry_run:
        console.print("⚡ [bold magenta]Agent 5 (Validator Dry-Run):[/bold magenta] Spinning up local PySpark session...")
        dry_res = validator.dry_run_script(str(script_file), temp_tables=ir_data.get("temporary_tables", []))
        if dry_res.get("dry_run_passed"):
            console.print("  └─ [bold green]PySpark Dry-Run PASSED![/bold green] (Spark Version: " + str(dry_res.get("spark_version")) + ")")
        else:
            console.print("  └─ [bold red]PySpark Dry-Run Failed:[/bold red] " + str(dry_res.get("error")))

    _render_dashboard(validated_steps)


def _render_dashboard(steps: list):
    table = Table(title="🎉 Multi-Agent Pipeline Execution Summary", show_header=True, header_style="bold magenta")
    table.add_column("Step ID", style="dim")
    table.add_column("Step Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Confidence", justify="right")
    table.add_column("AST Valid", justify="center")
    table.add_column("Optimizations", style="green")

    for s in steps:
        conf = int(s.get("confidence_score", 1.0) * 100)
        ast_ok = "✅" if s.get("validation", {}).get("ast_syntax_valid") else "❌"
        opts = len(s.get("optimizations", []))
        table.add_row(
            s.get("step_id", ""),
            s.get("name", "")[:30],
            s.get("block_type", ""),
            f"{conf}%",
            ast_ok,
            f"{opts} applied" if opts else "None"
        )

    console.print("\n")
    console.print(table)


if __name__ == "__main__":
    cli_app()
