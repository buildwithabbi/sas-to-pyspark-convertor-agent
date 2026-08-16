from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class BlockType(str, Enum):
    DATA_STEP = "DATA_STEP"
    PROC_SQL = "PROC_SQL"
    PROC_SORT = "PROC_SORT"
    PROC_TRANSPOSE = "PROC_TRANSPOSE"
    PROC_SUMMARY = "PROC_SUMMARY"
    PROC_MEANS = "PROC_MEANS"
    PROC_FREQ = "PROC_FREQ"
    PROC_IMPORT = "PROC_IMPORT"
    PROC_EXPORT = "PROC_EXPORT"
    PROC_FORMAT = "PROC_FORMAT"
    PROC_OTHER = "PROC_OTHER"
    MACRO_DEF = "MACRO_DEF"
    MACRO_CALL = "MACRO_CALL"
    LET_STATEMENT = "LET_STATEMENT"
    LIBNAME = "LIBNAME"
    UNKNOWN = "UNKNOWN"


class SASCodeBlock(BaseModel):
    id: str
    block_type: BlockType
    name: Optional[str] = None
    input_datasets: List[str] = Field(default_factory=list)
    output_datasets: List[str] = Field(default_factory=list)
    raw_code: str
    line_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EGPTaskNode(BaseModel):
    id: str
    label: str
    task_type: str
    code: Optional[str] = None
    input_tables: List[str] = Field(default_factory=list)
    output_tables: List[str] = Field(default_factory=list)
    upstream_ids: List[str] = Field(default_factory=list)
    downstream_ids: List[str] = Field(default_factory=list)
    xml_properties: Dict[str, Any] = Field(default_factory=dict)


class EGPProcessFlow(BaseModel):
    id: str
    name: str
    nodes: Dict[str, EGPTaskNode] = Field(default_factory=dict)
    execution_order: List[str] = Field(default_factory=list)


class ConvertedBlock(BaseModel):
    original_block: SASCodeBlock
    pyspark_code: str
    confidence_score: float = 1.0  # 0.0 to 1.0
    conversion_notes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    used_llm: bool = False


class ConversionResult(BaseModel):
    source_file: str
    file_type: str  # "sas" or "egp"
    converted_blocks: List[ConvertedBlock] = Field(default_factory=list)
    full_pyspark_script: str = ""
    notebook_json: Optional[Dict[str, Any]] = None
    warnings: List[str] = Field(default_factory=list)
    lineage: Dict[str, List[str]] = Field(default_factory=dict)
