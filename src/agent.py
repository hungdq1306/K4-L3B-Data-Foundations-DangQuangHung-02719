from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store (supports metadata filtering).
        2. Validate context relevance threshold (guardrail against irrelevant questions).
        3. Build a prompt with the chunks as context.
        4. Call the LLM to generate an answer.
    """

    def __init__(
        self,
        store: EmbeddingStore,
        llm_fn: Callable[[str], str],
        relevance_threshold: float | None = None,
        fallback_message: str | None = None,
    ) -> None:
        self.store = store
        self.llm_fn = llm_fn
        self.relevance_threshold = relevance_threshold
        self.fallback_message = fallback_message or (
            "Xin lỗi, câu hỏi này nằm ngoài phạm vi tài liệu chính sách được cung cấp trong hệ thống. "
            "Tôi chỉ có thể hỗ trợ giải đáp các quy định và chính sách liên quan đến Shopee."
        )

    def answer(
        self,
        question: str,
        top_k: int = 3,
        metadata_filter: dict | None = None,
        threshold: float | None = None,
    ) -> str:
        if metadata_filter:
            results = self.store.search_with_filter(question, top_k=top_k, metadata_filter=metadata_filter)
        else:
            results = self.store.search(question, top_k=top_k)

        effective_threshold = threshold if threshold is not None else self.relevance_threshold
        if effective_threshold is not None:
            if not results or results[0]["score"] < effective_threshold:
                return self.fallback_message

        context_texts = [r["content"] for r in results]
        context = "\n---\n".join(context_texts)
        prompt = (
            f"Context information:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer the question based on the provided context:"
        )
        return self.llm_fn(prompt)
