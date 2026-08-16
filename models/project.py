from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from models.step import SASStep, TranslatedStep


class SASProject(BaseModel):
    name: str
    source_file: str
    file_type: str  # "SAS" or "EGP"
    steps: List[SASStep] = Field(default_factory=list)
    libraries: List[str] = Field(default_factory=list)
    temporary_tables: List[str] = Field(default_factory=list)
    dag_execution_order: List[str] = Field(default_factory=list)


class MigrationReport(BaseModel):
    project_name: str
    source_file: str
    translated_steps: List[TranslatedStep] = Field(default_factory=list)
    full_pyspark_script: str = ""
    notebook_json: Optional[Dict[str, Any]] = None
    lineage_markdown: str = ""
    avg_confidence: float = 1.0
