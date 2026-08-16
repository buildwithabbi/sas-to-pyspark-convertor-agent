import re
import os
from typing import List, Optional
from sas2pyspark.models import SASCodeBlock, ConvertedBlock, BlockType
from sas2pyspark.transpiler import DataStepTranspiler, ProcTranspiler, MacroTranspiler
from sas2pyspark.parsers import SQLParser
from sas2pyspark.agent.prompts import SAS_CONVERSION_SYSTEM_PROMPT, USER_TRANSPILATION_PROMPT
from sas2pyspark.agent.validator import PySparkValidator
from sas2pyspark.config import config


class SAS2PySparkAgent:
    """Hybrid Conversion Engine: Combines deterministic AST/Rule Transpilers with AI Agent (Groq / Gemini)."""

    def __init__(self):
        self.data_step_transpiler = DataStepTranspiler()
        self.proc_transpiler = ProcTranspiler()
        self.sql_parser = SQLParser()
        self.macro_transpiler = MacroTranspiler()
        self.validator = PySparkValidator()

    def convert_block(self, block: SASCodeBlock) -> ConvertedBlock:
        """Converts a single SAS code block into PySpark code."""
        # Substitute any known macro variables
        cleaned_raw = self.macro_transpiler.substitute_macro_vars(block.raw_code)

        converted: Optional[ConvertedBlock] = None

        # 1. Rule-based conversion attempt
        if block.block_type == BlockType.LET_STATEMENT:
            converted = self.macro_transpiler.transpile_let(block)

        elif block.block_type == BlockType.PROC_SQL:
            sql_pyspark = self.sql_parser.translate_proc_sql(cleaned_raw)
            converted = ConvertedBlock(
                original_block=block,
                pyspark_code=sql_pyspark,
                confidence_score=0.95,
                conversion_notes=["Transpiled PROC SQL using sqlglot / Spark SQL engine"],
                used_llm=False
            )

        elif block.block_type.value.startswith("PROC_"):
            converted = self.proc_transpiler.transpile(block)

        elif block.block_type == BlockType.DATA_STEP:
            converted = self.data_step_transpiler.transpile(block)

        # 2. Check if LLM fallback is needed or requested
        provider = config.active_provider()
        should_use_llm = (
            config.enable_llm_fallback and
            provider in ("groq", "gemini") and (
                converted is None or
                converted.confidence_score < 0.85 or
                block.block_type in (BlockType.UNKNOWN, BlockType.PROC_OTHER, BlockType.MACRO_DEF)
            )
        )

        if should_use_llm:
            if provider == "groq":
                llm_result = self._convert_with_groq(block)
                if llm_result:
                    converted = llm_result
            elif provider == "gemini":
                llm_result = self._convert_with_gemini(block)
                if llm_result:
                    converted = llm_result

        # Fallback if converted is still None
        if converted is None:
            code_commented = "\n".join([f"# {line}" for line in block.raw_code.splitlines()])
            converted = ConvertedBlock(
                original_block=block,
                pyspark_code=f"# WARNING: Unrecognized block type {block.block_type}\n{code_commented}",
                confidence_score=0.3,
                warnings=[f"Could not automatically convert {block.block_type}"],
                used_llm=False
            )

        # 3. Validate generated code with AST parser
        valid, errs = self.validator.validate_code(converted.pyspark_code)
        if not valid:
            converted.warnings.extend([f"AST Validation error: {e}" for e in errs])
            converted.confidence_score *= 0.8

        return converted

    def _convert_with_groq(self, block: SASCodeBlock) -> Optional[ConvertedBlock]:
        """Queries Groq API (Llama 3.3 70B) with RAG vector examples to transpile complex SAS blocks."""
        try:
            from groq import Groq
            from agents.vector_store import SASVectorStore

            # Retrieve top RAG examples for few-shot context
            vstore = SASVectorStore()
            rag_examples = vstore.search_similar(block.raw_code, top_k=2)

            rag_context = ""
            if rag_examples:
                rag_context = "\n\n### Reference Conversion Examples:\n"
                for ex in rag_examples:
                    rag_context += f"\nExample ({ex['title']}):\nSAS:\n{ex['sas']}\nPySpark:\n{ex['pyspark']}\n"

            client = Groq(api_key=config.groq_api_key)
            prompt = USER_TRANSPILATION_PROMPT.format(
                block_type=block.block_type.value,
                input_datasets=", ".join(block.input_datasets),
                output_datasets=", ".join(block.output_datasets),
                raw_code=block.raw_code
            ) + rag_context

            completion = client.chat.completions.create(
                model=config.groq_model_name,
                messages=[
                    {"role": "system", "content": SAS_CONVERSION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2048,
            )

            raw_resp = completion.choices[0].message.content.strip()
            clean_code = re.sub(r'^```python\s*', '', raw_resp, flags=re.MULTILINE)
            clean_code = re.sub(r'^```\s*$', '', clean_code, flags=re.MULTILINE).strip()

            return ConvertedBlock(
                original_block=block,
                pyspark_code=clean_code,
                confidence_score=0.95,
                conversion_notes=[f"Converted using Groq AI Agent ({config.groq_model_name}) + RAG Examples"],
                used_llm=True
            )

        except Exception as e:
            return None

    def _convert_with_gemini(self, block: SASCodeBlock) -> Optional[ConvertedBlock]:
        """Queries Gemini LLM to transpile complex or unknown SAS blocks."""
        try:
            from google import genai

            client = genai.Client(api_key=config.gemini_api_key)
            prompt = USER_TRANSPILATION_PROMPT.format(
                block_type=block.block_type.value,
                input_datasets=", ".join(block.input_datasets),
                output_datasets=", ".join(block.output_datasets),
                raw_code=block.raw_code
            )

            response = client.models.generate_content(
                model=config.gemini_model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=SAS_CONVERSION_SYSTEM_PROMPT,
                    temperature=0.2,
                )
            )

            raw_resp = response.text.strip()
            clean_code = re.sub(r'^```python\s*', '', raw_resp, flags=re.MULTILINE)
            clean_code = re.sub(r'^```\s*$', '', clean_code, flags=re.MULTILINE).strip()

            return ConvertedBlock(
                original_block=block,
                pyspark_code=clean_code,
                confidence_score=0.92,
                conversion_notes=[f"Converted using Gemini AI Agent ({config.gemini_model_name})"],
                used_llm=True
            )

        except Exception as e:
            return None
