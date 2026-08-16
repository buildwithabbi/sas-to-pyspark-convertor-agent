import re
from typing import List, Tuple
from models.step import SASStep, StepType
from parser.tokenizer import SASTokenizer


class SASParser:
    """Parses SAS code into structured SASSteps."""

    def __init__(self):
        self.tokenizer = SASTokenizer()

    def parse_script(self, sas_code: str) -> List[SASStep]:
        tokens = self.tokenizer.tokenize(sas_code)
        steps: List[SASStep] = []

        for idx, (block_str, line_num) in enumerate(tokens, 1):
            step_type = self._identify_step_type(block_str)
            inputs, outputs = self._extract_datasets(block_str, step_type)
            name = self._extract_step_name(block_str, step_type)

            step = SASStep(
                id=f"step_{idx}",
                step_type=step_type,
                name=name,
                input_datasets=inputs,
                output_datasets=outputs,
                raw_code=block_str,
                line_number=line_num
            )
            steps.append(step)

        return steps

    def _identify_step_type(self, block: str) -> StepType:
        block_upper = block.strip().upper()
        if block_upper.startswith("DATA"):
            return StepType.DATA_STEP
        elif block_upper.startswith("PROC SQL"):
            return StepType.PROC_SQL
        elif block_upper.startswith("PROC SORT"):
            return StepType.PROC_SORT
        elif block_upper.startswith("PROC TRANSPOSE"):
            return StepType.PROC_TRANSPOSE
        elif block_upper.startswith("PROC SUMMARY"):
            return StepType.PROC_SUMMARY
        elif block_upper.startswith("PROC MEANS"):
            return StepType.PROC_MEANS
        elif block_upper.startswith("PROC FREQ"):
            return StepType.PROC_FREQ
        elif block_upper.startswith("PROC IMPORT"):
            return StepType.PROC_IMPORT
        elif block_upper.startswith("PROC EXPORT"):
            return StepType.PROC_EXPORT
        elif block_upper.startswith("PROC FORMAT") or "<CREATEIMPORTEDFORMATSTATE" in block_upper:
            return StepType.PROC_FORMAT
        elif block_upper.startswith("PROC"):
            return StepType.PROC_OTHER
        elif block_upper.startswith("%MACRO"):
            return StepType.MACRO_DEF
        elif block_upper.startswith("%LET"):
            return StepType.LET_STATEMENT
        elif block_upper.startswith("LIBNAME"):
            return StepType.LIBNAME
        elif block_upper.startswith("%"):
            return StepType.MACRO_CALL
        return StepType.UNKNOWN

    def _extract_datasets(self, block: str, step_type: StepType) -> Tuple[List[str], List[str]]:
        inputs, outputs = [], []

        if step_type == StepType.DATA_STEP:
            data_m = re.search(r'(?i)\bDATA\s+([^;]+);', block)
            if data_m:
                raw_outs = data_m.group(1).strip().split()
                for out in raw_outs:
                    cleaned = re.sub(r'\(.*?\)', '', out).strip()
                    if cleaned and not cleaned.startswith('('):
                        outputs.append(cleaned)

            set_matches = re.findall(r'(?i)\b(?:SET|MERGE)\s+([^;]+);', block)
            for sm in set_matches:
                raw_ins = sm.strip().split()
                for inp in raw_ins:
                    cleaned = re.sub(r'\(.*?\)', '', inp).strip()
                    if cleaned and not cleaned.upper() in ('KEY=', 'NOBS=', 'END='):
                        inputs.append(cleaned)

        elif step_type == StepType.PROC_SQL:
            from_matches = re.findall(r'(?i)\b(?:FROM|JOIN)\s+([a-zA-Z0-9_\.]+)', block)
            inputs.extend(from_matches)
            create_match = re.search(r'(?i)\bCREATE\s+TABLE\s+([a-zA-Z0-9_\.]+)', block)
            if create_match:
                outputs.append(create_match.group(1))

        elif step_type in (StepType.PROC_SORT, StepType.PROC_TRANSPOSE, StepType.PROC_SUMMARY, StepType.PROC_MEANS, StepType.PROC_FREQ):
            data_m = re.search(r'(?i)\bDATA\s*=\s*([a-zA-Z0-9_\.]+)', block)
            if data_m:
                inputs.append(data_m.group(1))
            out_m = re.search(r'(?i)\bOUT\s*=\s*([a-zA-Z0-9_\.]+)', block)
            if out_m:
                outputs.append(out_m.group(1))

        return list(dict.fromkeys(inputs)), list(dict.fromkeys(outputs))

    def _extract_step_name(self, block: str, step_type: StepType) -> str:
        if step_type == StepType.DATA_STEP:
            m = re.search(r'(?i)\bDATA\s+([a-zA-Z0-9_\.]+)', block)
            return f"data_step_{m.group(1)}" if m else "data_step"
        elif step_type == StepType.PROC_SQL:
            m = re.search(r'(?i)\bCREATE\s+TABLE\s+([a-zA-Z0-9_\.]+)', block)
            return f"proc_sql_{m.group(1)}" if m else "proc_sql"
        elif step_type.value.startswith("PROC_"):
            return step_type.value.lower()
        return step_type.value.lower()
