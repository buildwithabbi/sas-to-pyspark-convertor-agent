from typing import Dict, Any, List
from sas2pyspark.models import SASCodeBlock, BlockType
from sas2pyspark.agent.llm_agent import SAS2PySparkAgent
from agents.knowledge import SASKnowledgeAgent


class SASTranslatorAgent:
    """Agent 3 - Translator: Converts each analyzed SAS IR step into PySpark code."""

    def __init__(self):
        self.hybrid_agent = SAS2PySparkAgent()
        self.knowledge_agent = SASKnowledgeAgent()

    def translate_step(self, step_ir: Dict[str, Any]) -> Dict[str, Any]:
        """Translates a single IR step dictionary into PySpark code."""
        block_type_val = step_ir.get("type", "UNKNOWN")
        try:
            b_type = BlockType(block_type_val)
        except ValueError:
            b_type = BlockType.UNKNOWN

        block = SASCodeBlock(
            id=step_ir.get("id", "step_1"),
            block_type=b_type,
            name=step_ir.get("name"),
            input_datasets=step_ir.get("inputs", []),
            output_datasets=step_ir.get("outputs", []),
            raw_code=step_ir.get("raw_code", "")
        )

        converted = self.hybrid_agent.convert_block(block)

        # Lookup construct knowledge mapping
        mapping_info = self.knowledge_agent.lookup(block_type_val)

        return {
            "step_id": step_ir.get("id"),
            "name": step_ir.get("name"),
            "block_type": block_type_val,
            "pyspark_code": converted.pyspark_code,
            "confidence_score": converted.confidence_score,
            "notes": converted.conversion_notes,
            "warnings": converted.warnings,
            "knowledge_mapping": mapping_info
        }

    def translate_all(self, ir_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        translated_steps = []
        for step in ir_data.get("steps", []):
            res = self.translate_step(step)
            translated_steps.append(res)
        return translated_steps
