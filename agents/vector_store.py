import json
from pathlib import Path
from typing import List, Dict, Any

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class SASVectorStore:
    """RAG Vector Store Agent: Stores historical SAS-to-PySpark translation examples and retrieves top-k relevant patterns."""

    def __init__(self, examples_file: str = "/home/abhishek/sas-to-pyspark-convertor-agent/knowledge/examples.json"):
        self.examples_path = Path(examples_file)
        self.examples: List[Dict[str, Any]] = []
        self.chroma_client = None
        self.collection = None
        self._initialize_store()

    def _initialize_store(self):
        if not self.examples_path.exists():
            return

        self.examples = json.loads(self.examples_path.read_text(encoding='utf-8'))
        if not self.examples:
            return

        if HAS_CHROMADB:
            try:
                self.chroma_client = chromadb.Client(Settings(anonymized_telemetry=False))
                self.collection = self.chroma_client.get_or_create_collection(name="sas_examples")
                
                documents = [f"{ex['title']}\n{ex['sas']}" for ex in self.examples]
                ids = [f"ex_{idx}" for idx in range(len(self.examples))]
                metadatas = [{"title": ex["title"], "pyspark": ex["pyspark"]} for ex in self.examples]

                self.collection.add(documents=documents, ids=ids, metadatas=metadatas)
            except Exception:
                self.chroma_client = None

        if HAS_SKLEARN:
            self.vectorizer = TfidfVectorizer()
            texts = [f"{ex['title']} {ex['sas']}" for ex in self.examples]
            self.tfidf_matrix = self.vectorizer.fit_transform(texts)

    def search_similar(self, query_sas: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Queries the vector store for top_k relevant SAS-to-PySpark translation examples."""
        if not self.examples:
            return []

        if HAS_CHROMADB and self.collection:
            try:
                results = self.collection.query(query_texts=[query_sas], n_results=min(top_k, len(self.examples)))
                retrieved = []
                if results and "documents" in results and results["documents"]:
                    docs = results["documents"][0]
                    metas = results["metadatas"][0]
                    for d, m in zip(docs, metas):
                        retrieved.append({
                            "title": m.get("title", ""),
                            "sas": d,
                            "pyspark": m.get("pyspark", "")
                        })
                return retrieved
            except Exception:
                pass

        if HAS_SKLEARN:
            query_vec = self.vectorizer.transform([query_sas])
            scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            top_indices = scores.argsort()[::-1][:top_k]
            return [self.examples[idx] for idx in top_indices if idx < len(self.examples)]

        # Pure Python Keyword Matching Fallback
        query_words = set(query_sas.lower().split())
        scored = []
        for ex in self.examples:
            ex_words = set(f"{ex['title']} {ex['sas']}".lower().split())
            overlap = len(query_words.intersection(ex_words))
            scored.append((overlap, ex))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[:top_k]]
