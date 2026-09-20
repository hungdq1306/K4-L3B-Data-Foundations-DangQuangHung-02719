#!/usr/bin/env python3
"""Web application server for Shopee AI Policy Assistant (Day 7 - Lab Data Foundations).

Provides a premium web UI matching the Shopee Orange/Coral aesthetic with:
  - Interactive chat with RAG Agent
  - Audience filtering ('buyer' / 'seller' / 'both')
  - Out-of-Domain Guardrail visualization (refusing irrelevant inquiries)
  - Real-time RAG Inspection panel (Top-k chunks, Cosine Similarity, Source metadata)
  - 1-Click Benchmark Query execution
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from bench import BENCHMARK_QUERIES, load_and_chunk_corpus
from demo import OUT_OF_DOMAIN_PATTERNS, POLICY_KEYWORDS, check_domain_relevance, smart_llm_response
from src.chunking import HeadingChunker
from src.embeddings import _mock_embed
from src.store import EmbeddingStore

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"

app = FastAPI(title="Shopee Policy AI Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Knowledge Base state
STATE: Dict[str, Any] = {
    "store": None,
    "total_chunks": 0,
    "total_docs": 0,
    "strategy": "HeadingChunker (Bảo toàn Tiêu đề)",
    "data_dir": "data/shopee",
}


def init_knowledge_base():
    data_dir = BASE_DIR / "data" / "shopee"
    if not data_dir.exists():
        data_dir = BASE_DIR / "data"

    chunker = HeadingChunker(chunk_size=500)
    documents = load_and_chunk_corpus(data_dir, chunker)

    store = EmbeddingStore(collection_name="web_demo_store", embedding_fn=_mock_embed)
    store.add_documents(documents)

    md_files = list(data_dir.glob("*.md"))
    STATE["store"] = store
    STATE["total_chunks"] = len(documents)
    STATE["total_docs"] = len(md_files)
    STATE["data_dir"] = str(data_dir.relative_to(BASE_DIR))
    print(f"Loaded {STATE['total_docs']} files -> {STATE['total_chunks']} chunks into EmbeddingStore.")


class ChatRequest(BaseModel):
    query: str
    audience: Optional[str] = "both"
    top_k: Optional[int] = 3


class ChunkResponse(BaseModel):
    doc_id: str
    title: str
    score: float
    content: str
    audience: str
    source_url: str


class ChatResponse(BaseModel):
    query: str
    audience: str
    is_relevant: bool
    answer: str
    chunks: List[ChunkResponse]
    guardrail_status: str


@app.on_event("startup")
def startup_event():
    init_knowledge_base()


@app.get("/api/stats")
def get_stats():
    return {
        "total_docs": STATE["total_docs"],
        "total_chunks": STATE["total_chunks"],
        "strategy": STATE["strategy"],
        "data_dir": STATE["data_dir"],
        "embedding_backend": "Deterministic Mock Embeddings (_mock_embed)",
    }


@app.get("/api/queries")
def get_preset_queries():
    presets = []
    for q in BENCHMARK_QUERIES:
        presets.append({
            "id": q["id"],
            "query": q["query"],
            "audience": q["filter"].get("audience", "both"),
            "category": "benchmark",
            "label": f"Câu #{q['id']} ({'Người mua' if q['filter'].get('audience') == 'buyer' else 'Người bán'})",
            "gold_answer": q["gold_answer"],
        })
    # Add out-of-domain test queries
    presets.append({
        "id": "irr_1",
        "query": "Thủ đô của nước Pháp là gì và dân số hiện tại là bao nhiêu?",
        "audience": "both",
        "category": "irrelevant",
        "label": "Test Lạc đề #1 (Địa lý)",
        "gold_answer": "Từ chối trả lời do nằm ngoài phạm vi chính sách Shopee.",
    })
    presets.append({
        "id": "irr_2",
        "query": "Hướng dẫn công thức nấu món phở bò truyền thống ngon đậm đà tại nhà?",
        "audience": "both",
        "category": "irrelevant",
        "label": "Test Lạc đề #2 (Ẩm thực)",
        "gold_answer": "Từ chối trả lời do nằm ngoài phạm vi chính sách Shopee.",
    })
    presets.append({
        "id": "irr_3",
        "query": "Thời tiết ngày mai ở Hà Nội có mưa không và nhiệt độ bao nhiêu?",
        "audience": "both",
        "category": "irrelevant",
        "label": "Test Lạc đề #3 (Thời tiết)",
        "gold_answer": "Từ chối trả lời do nằm ngoài phạm vi chính sách Shopee.",
    })
    return presets


@app.post("/api/chat", response_model=ChatResponse)
def handle_chat(req: ChatRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    store: EmbeddingStore = STATE["store"]
    if not store:
        raise HTTPException(status_code=500, detail="Knowledge base not initialized.")

    audience = (req.audience or "both").lower().strip()
    is_relevant = check_domain_relevance(query)

    if not is_relevant:
        answer = smart_llm_response("", is_relevant=False)
        return ChatResponse(
            query=query,
            audience=audience,
            is_relevant=False,
            answer=answer,
            chunks=[],
            guardrail_status="REJECTED_OUT_OF_DOMAIN",
        )

    # Retrieval
    meta_filter = {"audience": audience} if audience in ["buyer", "seller"] else None
    if meta_filter:
        raw_results = store.search_with_filter(query, top_k=req.top_k, metadata_filter=meta_filter)
    else:
        raw_results = store.search(query, top_k=req.top_k)

    chunks: List[ChunkResponse] = []
    for r in raw_results:
        meta = r.get("metadata", {})
        doc_id = meta.get("doc_id", "unknown").split("#")[0]
        title = meta.get("title") or doc_id.replace("-", " ").title()
        source_url = meta.get("source_url") or "https://help.shopee.vn"
        aud = meta.get("audience", "both")
        score = float(r.get("score", 0.0))
        content = r.get("content", "")
        chunks.append(ChunkResponse(
            doc_id=doc_id,
            title=title,
            score=round(score, 4),
            content=content,
            audience=aud,
            source_url=source_url,
        ))

    context_text = "\n---\n".join([c.content for c in chunks])
    prompt = f"Context: {context_text}\nQuestion: {query}"
    answer = smart_llm_response(prompt, is_relevant=True)

    return ChatResponse(
        query=query,
        audience=audience,
        is_relevant=True,
        answer=answer,
        chunks=chunks,
        guardrail_status="ACCEPTED_IN_DOMAIN",
    )


# Serve static frontend files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return {"message": "Static assets loading..."}
    return FileResponse(index_file)


if __name__ == "__main__":
    port = 8000
    print(f"Starting Shopee Policy AI Assistant Web UI on http://localhost:{port}")
    uvicorn.run("run_web:app", host="127.0.0.1", port=port, reload=False)
