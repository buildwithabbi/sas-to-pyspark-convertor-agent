from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class StepType(str, Enum):
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


class SASStep(BaseModel):
    id: str
    step_type: StepType
    name: Optional[str] = None
    input_datasets: List[str] = Field(default_factory=list)
    output_datasets: List[str] = Field(default_factory=list)
    raw_code: str
    line_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TranslatedStep(BaseModel):
    step: SASStep
    pyspark_code: str
    confidence_score: float = 1.0
    notes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    optimizations: List[str] = Field(default_factory=list)
    validation: Dict[str, Any] = Field(default_factory=dict)
