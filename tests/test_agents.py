import pytest
from agents import (
    SASAnalyzerAgent,
    SASKnowledgeAgent,
    SASTranslatorAgent,
    PySparkOptimizerAgent,
    PySparkValidatorAgent,
    DocumentationAgent
)
from agents.vector_store import SASVectorStore


def test_knowledge_agent():
    k_agent = SASKnowledgeAgent()
    mappings = k_agent.get_all_mappings()
    assert len(mappings) > 0

    sort_mapping = k_agent.lookup("PROC SORT")
    assert sort_mapping is not None
    assert sort_mapping["pyspark_equivalent"] == "DataFrame sort / dropDuplicates"


def test_optimizer_agent():
    opt_agent = PySparkOptimizerAgent()
    code = "df_collect = df.collect()"
    opt_code, opts = opt_agent.optimize_code(code)

    assert ".take(100)" in opt_code
    assert len(opts) == 1


def test_rag_vector_store():
    vstore = SASVectorStore()
    results = vstore.search_similar("PROC SORT DATA=work.sales", top_k=1)
    assert len(results) >= 1
    assert "PROC SORT" in results[0]["sas"]
