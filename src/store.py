from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        try:
            import chromadb

            client = chromadb.Client()
            try:
                client.delete_collection(name=collection_name)
            except Exception:
                pass
            self._collection = client.create_collection(name=collection_name)
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        meta = dict(doc.metadata) if doc.metadata else {}
        meta["doc_id"] = doc.id
        return {
            "id": doc.id,
            "content": doc.content,
            "metadata": meta,
            "embedding": self._embedding_fn(doc.content),
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if not records:
            return []
        query_emb = self._embedding_fn(query)
        scored = []
        for rec in records:
            score = _dot(query_emb, rec["embedding"])
            scored.append({
                "id": rec["id"],
                "content": rec["content"],
                "metadata": rec.get("metadata", {}),
                "score": score,
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for doc in docs:
            self._next_index += 1
            record = self._make_record(doc)
            self._store.append(record)
            chunk_id = f"{doc.id}_{self._next_index}"
            ids.append(chunk_id)
            documents.append(record["content"])
            embeddings.append(record["embedding"])
            metadatas.append(record["metadata"])

        if self._use_chroma and self._collection is not None and ids:
            try:
                self._collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
            except Exception:
                pass

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        if self._use_chroma and self._collection is not None and self._collection.count() > 0:
            query_emb = self._embedding_fn(query)
            res = self._collection.query(query_embeddings=[query_emb], n_results=top_k)
            results = []
            if res and res.get("ids") and len(res["ids"][0]) > 0:
                ids = res["ids"][0]
                documents = res["documents"][0] if res.get("documents") else [""] * len(ids)
                metadatas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(ids)
                distances = res["distances"][0] if res.get("distances") else [0.0] * len(ids)
                for i in range(len(ids)):
                    score = 1.0 - distances[i] if distances else 0.0
                    meta = metadatas[i] or {}
                    doc_id = meta.get("doc_id", ids[i])
                    results.append({
                        "id": doc_id,
                        "content": documents[i],
                        "metadata": meta,
                        "score": score,
                    })
                return results
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        if self._use_chroma and self._collection is not None:
            return self._collection.count()
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            return self.search(query, top_k=top_k)

        filtered_records = []
        for record in self._store:
            meta = record.get("metadata", {})
            if all(meta.get(k) == v for k, v in metadata_filter.items()):
                filtered_records.append(record)

        return self._search_records(query, filtered_records, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        initial_count = len(self._store)
        self._store = [
            rec for rec in self._store
            if rec["id"] != doc_id and rec.get("metadata", {}).get("doc_id") != doc_id
        ]
        removed = len(self._store) < initial_count

        if self._use_chroma and self._collection is not None:
            try:
                self._collection.delete(where={"doc_id": doc_id})
            except Exception:
                try:
                    self._collection.delete(ids=[doc_id])
                except Exception:
                    pass

        return removed
