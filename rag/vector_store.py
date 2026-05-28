"""
rag/vector_store.py
ChromaDB vector store for career knowledge base.
Loads markdown docs from rag/knowledge_base/ and enables semantic retrieval.
"""

import os
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

KB_DIR = Path(__file__).parent / "knowledge_base"
CHROMA_DIR = Path(".cache/chromadb")

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    _client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    _collection = _client.get_or_create_collection(
        name="career_knowledge",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    # Populate if empty
    if _collection.count() == 0:
        _load_knowledge_base(_collection)

    return _collection


def _load_knowledge_base(collection) -> None:
    """Load all markdown files from knowledge_base/ into ChromaDB."""
    docs, ids, metas = [], [], []
    doc_id = 0

    for md_file in sorted(KB_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        # Split on double newlines to create chunks
        chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 50]
        for chunk in chunks:
            docs.append(chunk)
            ids.append(f"doc_{doc_id}")
            metas.append({"source": md_file.name})
            doc_id += 1

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metas)


def retrieve(query: str, n_results: int = 4) -> str:
    """
    Retrieve top-n relevant chunks from the career knowledge base.
    Returns a formatted string for injection into the career agent prompt.
    """
    collection = _get_collection()
    if collection.count() == 0:
        return "No knowledge base documents available."

    results = collection.query(query_texts=[query], n_results=min(n_results, collection.count()))
    documents = results.get("documents", [[]])[0]
    sources = [m.get("source", "") for m in results.get("metadatas", [[]])[0]]

    formatted = []
    for doc, src in zip(documents, sources):
        formatted.append(f"[Source: {src}]\n{doc}")

    return "\n\n---\n\n".join(formatted)


def rebuild_index() -> int:
    """Force-rebuild the ChromaDB index. Returns document count."""
    global _collection
    if _client and _collection:
        try:
            _client.delete_collection("career_knowledge")
        except Exception:
            pass
        _collection = None
    collection = _get_collection()
    return collection.count()
