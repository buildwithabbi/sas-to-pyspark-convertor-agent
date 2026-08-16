import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from agents.vector_store import SASVectorStore


class SASKnowledgeAgent:
    """Agent 2 - SAS Knowledge Agent: Maintains SAS-to-PySpark construct mappings and RAG vector search for conversion patterns."""

    def __init__(self):
        self.mapping_file = Path("/home/abhishek/sas-to-pyspark-convertor-agent/knowledge/sas_mapping.json")
        self.examples_file = Path("/home/abhishek/sas-to-pyspark-convertor-agent/knowledge/examples.json")
        self.mappings: List[Dict[str, Any]] = []
        self.examples: List[Dict[str, Any]] = []
        self.vector_store = SASVectorStore(str(self.examples_file))
        self._load_knowledge()

    def _load_knowledge(self):
        if self.mapping_file.exists():
            data = json.loads(self.mapping_file.read_text(encoding='utf-8'))
            self.mappings = data.get("mappings", [])
        if self.examples_file.exists():
            self.examples = json.loads(self.examples_file.read_text(encoding='utf-8'))

    def lookup(self, sas_construct: str) -> Optional[Dict[str, Any]]:
        for m in self.mappings:
            if m["sas_construct"].lower() in sas_construct.lower() or sas_construct.lower() in m["sas_construct"].lower():
                return m
        return None

    def get_all_mappings(self) -> List[Dict[str, Any]]:
        return self.mappings

    def get_examples(self) -> List[Dict[str, Any]]:
        return self.examples

    def query_rag_examples(self, query_sas: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Queries RAG vector store for top_k relevant translation examples."""
        return self.vector_store.search_similar(query_sas, top_k=top_k)
