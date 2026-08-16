import json
from typing import List, Dict, Any
from pathlib import Path
from sas2pyspark.parsers.sas_parser import SASParser
from sas2pyspark.parsers.egp_parser import EGPParser
from sas2pyspark.models import SASCodeBlock, EGPProcessFlow


class SASAnalyzerAgent:
    """Agent 1 - SAS Analyzer: Parses SAS & EGP scripts into Intermediate Representation JSON (AST/IR)."""

    def __init__(self):
        self.sas_parser = SASParser()
        self.egp_parser = EGPParser()

    def analyze(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if path.suffix.lower() == '.egp' or (path.is_dir() and (path / "project.xml").exists()):
            flow = self.egp_parser.parse(str(path))
            return self._analyze_egp_flow(flow, str(path))
        else:
            code = path.read_text(encoding='utf-8', errors='ignore')
            return self._analyze_sas_script(code, str(path))

    def _analyze_sas_script(self, sas_code: str, source: str) -> Dict[str, Any]:
        blocks = self.sas_parser.parse_script(sas_code)
        steps = []
        temp_tables = set()
        libraries = set()

        for idx, b in enumerate(blocks, 1):
            inputs = [ds.replace('WORK.', '').replace('work.', '') for ds in b.input_datasets]
            outputs = [ds.replace('WORK.', '').replace('work.', '') for ds in b.output_datasets]

            temp_tables.update(inputs)
            temp_tables.update(outputs)

            for ds in b.input_datasets + b.output_datasets:
                if '.' in ds:
                    libraries.add(ds.split('.')[0])

            steps.append({
                "id": f"step_{idx}",
                "type": b.block_type.value,
                "name": b.name or f"step_{idx}",
                "input": inputs[0] if inputs else None,
                "inputs": inputs,
                "output": outputs[0] if outputs else None,
                "outputs": outputs,
                "raw_code": b.raw_code,
                "line_number": b.line_number
            })

        return {
            "source_file": source,
            "file_type": "SAS",
            "libraries": list(libraries),
            "temporary_tables": list(temp_tables),
            "steps": steps
        }

    def _analyze_egp_flow(self, flow: EGPProcessFlow, source: str) -> Dict[str, Any]:
        steps = []
        temp_tables = set()
        libraries = set()

        step_idx = 1
        for node_id in flow.execution_order:
            node = flow.nodes[node_id]
            if node.code:
                blocks = self.sas_parser.parse_script(node.code)
                for b in blocks:
                    inputs = [ds.replace('WORK.', '').replace('work.', '') for ds in b.input_datasets]
                    outputs = [ds.replace('WORK.', '').replace('work.', '') for ds in b.output_datasets]

                    temp_tables.update(inputs)
                    temp_tables.update(outputs)

                    for ds in b.input_datasets + b.output_datasets:
                        if '.' in ds:
                            libraries.add(ds.split('.')[0])

                    steps.append({
                        "id": f"step_{step_idx}",
                        "type": b.block_type.value,
                        "name": f"{node.label}_{b.name or b.block_type.value}",
                        "input": inputs[0] if inputs else None,
                        "inputs": inputs,
                        "output": outputs[0] if outputs else None,
                        "outputs": outputs,
                        "raw_code": b.raw_code,
                        "line_number": b.line_number
                    })
                    step_idx += 1

        return {
            "source_file": source,
            "file_type": "EGP",
            "process_flow_name": flow.name,
            "libraries": list(libraries),
            "temporary_tables": list(temp_tables),
            "steps": steps
        }
