import os
import json
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from sas2pyspark import __version__
from sas2pyspark.models import ConversionResult, ConvertedBlock
from sas2pyspark.parsers import SASParser, EGPParser
from sas2pyspark.agent import SAS2PySparkAgent
from sas2pyspark.generator import ScriptBuilder, NotebookBuilder

app = typer.Typer(
    name="sas2pyspark",
    help="⚡ Production-grade AI Agent to convert SAS (.sas) scripts and Enterprise Guide (.egp) projects to PySpark code."
)
console = Console()


@app.command()
def convert(
    input_path: str = typer.Argument(..., help="Path to input SAS script (.sas) or EGP file (.egp) or directory"),
    output_dir: str = typer.Option("./converted_output", "--out", "-o", help="Output directory for generated PySpark files"),
    format: str = typer.Option("both", "--format", "-f", help="Output format: 'script' (.py), 'notebook' (.ipynb), or 'both'"),
    dump_ir: bool = typer.Option(False, "--dump-ir", help="Export Intermediate Representation JSON (AST/IR)"),
):
    """Converts a SAS script or EGP project into production-ready PySpark code."""
    path = Path(input_path)
    if not path.exists():
        console.print(f"[bold red]Error:[/bold red] Path '{input_path}' does not exist.")
        raise typer.Exit(code=1)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    agent = SAS2PySparkAgent()
    converted_results: list[ConversionResult] = []

    if path.is_file():
        if path.suffix.lower() == '.sas':
            res = _convert_sas_file(path, agent, out_path, format, dump_ir)
            converted_results.append(res)
        elif path.suffix.lower() == '.egp':
            res = _convert_egp_path(path, agent, out_path, format, dump_ir)
            converted_results.append(res)
        else:
            console.print(f"[bold red]Error:[/bold red] Unsupported file extension '{path.suffix}'. Use .sas or .egp.")
            raise typer.Exit(code=1)
    elif path.is_dir():
        # Check if directory itself is an unzipped EGP project (has project.xml)
        if (path / "project.xml").exists() or list(path.glob("**/project.xml")):
            res = _convert_egp_path(path, agent, out_path, format, dump_ir)
            converted_results.append(res)
        else:
            # Batch process all SAS & EGP files in directory
            sas_files = list(path.glob("**/*.sas"))
            egp_files = list(path.glob("**/*.egp"))
            console.print(f"[bold blue]Found {len(sas_files)} .sas files and {len(egp_files)} .egp files[/bold blue]")

            for sf in sas_files:
                converted_results.append(_convert_sas_file(sf, agent, out_path / sf.stem, format, dump_ir))
            for ef in egp_files:
                converted_results.append(_convert_egp_path(ef, agent, out_path / ef.stem, format, dump_ir))

    # Display Conversion Summary Dashboard
    _render_summary_dashboard(converted_results)


def _convert_sas_file(sas_path: Path, agent: SAS2PySparkAgent, out_dir: Path, format_type: str, dump_ir: bool = False) -> ConversionResult:
    console.print(f"[bold cyan]Processing SAS Script:[/bold cyan] [underline]{sas_path.name}[/underline]")
    parser = SASParser()
    sas_code = sas_path.read_text(encoding='utf-8', errors='ignore')
    blocks = parser.parse_script(sas_code)

    converted_blocks: list[ConvertedBlock] = []
    for block in blocks:
        conv = agent.convert_block(block)
        converted_blocks.append(conv)

    script_code = ScriptBuilder.build_script(converted_blocks, sas_path.name)
    notebook_dict = NotebookBuilder.build_notebook(converted_blocks, sas_path.name)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_script = out_dir / f"{sas_path.stem}_converted.py"
    out_notebook = out_dir / f"{sas_path.stem}_converted.ipynb"

    if format_type in ("script", "both"):
        out_script.write_text(script_code, encoding='utf-8')
        console.print(f"  └─ Generated PySpark Script: [bold green]{out_script}[/bold green]")

    if format_type in ("notebook", "both"):
        out_notebook.write_text(json.dumps(notebook_dict, indent=2), encoding='utf-8')
        console.print(f"  └─ Generated Notebook: [bold green]{out_notebook}[/bold green]")

    if dump_ir:
        ir_json = [b.original_block.model_dump() for b in converted_blocks]
        out_ir = out_dir / f"{sas_path.stem}_ast_ir.json"
        out_ir.write_text(json.dumps(ir_json, indent=2), encoding='utf-8')
        console.print(f"  └─ Exported Intermediate AST JSON: [bold yellow]{out_ir}[/bold yellow]")

    return ConversionResult(
        source_file=str(sas_path),
        file_type="sas",
        converted_blocks=converted_blocks,
        full_pyspark_script=script_code,
        notebook_json=notebook_dict
    )


def _convert_egp_path(egp_path: Path, agent: SAS2PySparkAgent, out_dir: Path, format_type: str, dump_ir: bool = False) -> ConversionResult:
    console.print(f"[bold cyan]Processing EGP Project:[/bold cyan] [underline]{egp_path.name}[/underline]")
    egp_parser = EGPParser()
    flow = egp_parser.parse(str(egp_path))

    sas_parser = SASParser()
    all_converted: list[ConvertedBlock] = []

    for node_id in flow.execution_order:
        node = flow.nodes[node_id]
        if node.code:
            blocks = sas_parser.parse_script(node.code)
            for b in blocks:
                b.name = f"{node.label}_{b.name or b.block_type.value}"
                conv = agent.convert_block(b)
                all_converted.append(conv)

    script_code = ScriptBuilder.build_script(all_converted, egp_path.name, flow)
    notebook_dict = NotebookBuilder.build_notebook(all_converted, egp_path.name, flow)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_script = out_dir / f"{egp_path.stem}_pipeline.py"
    out_notebook = out_dir / f"{egp_path.stem}_pipeline.ipynb"

    if format_type in ("script", "both"):
        out_script.write_text(script_code, encoding='utf-8')
        console.print(f"  └─ Generated PySpark Script: [bold green]{out_script}[/bold green]")

    if format_type in ("notebook", "both"):
        out_notebook.write_text(json.dumps(notebook_dict, indent=2), encoding='utf-8')
        console.print(f"  └─ Generated Notebook: [bold green]{out_notebook}[/bold green]")

    if dump_ir:
        ir_json = [b.original_block.model_dump() for b in all_converted]
        out_ir = out_dir / f"{egp_path.stem}_ast_ir.json"
        out_ir.write_text(json.dumps(ir_json, indent=2), encoding='utf-8')
        console.print(f"  └─ Exported Intermediate AST JSON: [bold yellow]{out_ir}[/bold yellow]")

    return ConversionResult(
        source_file=str(egp_path),
        file_type="egp",
        converted_blocks=all_converted,
        full_pyspark_script=script_code,
        notebook_json=notebook_dict
    )


def _render_summary_dashboard(results: list[ConversionResult]):
    table = Table(title="🎉 Conversion Summary Dashboard", show_header=True, header_style="bold magenta")
    table.add_column("Source File", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Blocks", justify="right")
    table.add_column("Avg Confidence", justify="right")
    table.add_column("Status", style="bold green")

    for res in results:
        tot_blocks = len(res.converted_blocks)
        avg_conf = sum(b.confidence_score for b in res.converted_blocks) / tot_blocks if tot_blocks else 1.0
        conf_str = f"{int(avg_conf * 100)}%"
        conf_style = "bold green" if avg_conf > 0.85 else "bold yellow" if avg_conf > 0.7 else "bold red"
        status = "✅ Success" if avg_conf > 0.7 else "⚠️ Warnings"

        table.add_row(
            Path(res.source_file).name,
            res.file_type.upper(),
            str(tot_blocks),
            f"[{conf_style}]{conf_str}[/{conf_style}]",
            status
        )

    console.print("\n")
    console.print(table)


@app.command()
def inspect(egp_path: str = typer.Argument(..., help="Path to .egp file or unzipped project directory")):
    """Inspects an Enterprise Guide (.egp) project flow and prints DAG node dependencies."""
    parser = EGPParser()
    flow = parser.parse(egp_path)

    tree = Tree(f"📁 [bold gold1]EGP Project Flow: {flow.name}[/bold gold1]")
    for node_id in flow.execution_order:
        node = flow.nodes[node_id]
        has_code = "💻 [green]Has SAS Code[/green]" if node.code else "📄 [yellow]No Code[/yellow]"
        branch = tree.add(f"⚙️ [bold white]{node.label}[/bold white] (ID: [dim]{node_id}[/dim]) - {has_code}")
        if node.upstream_ids:
            branch.add(f"⬅️ Upstream: {', '.join(node.upstream_ids)}")
        if node.downstream_ids:
            branch.add(f"➡️ Downstream: {', '.join(node.downstream_ids)}")

    console.print(tree)


@app.command()
def version():
    """Prints sas2pyspark version."""
    console.print(f"sas2pyspark AI Agent version [bold cyan]{__version__}[/bold cyan]")


if __name__ == "__main__":
    app()
