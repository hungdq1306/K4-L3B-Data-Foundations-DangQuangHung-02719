#!/usr/bin/env python3
"""Benchmark suite & demo evaluator for Day 7 Data Foundations (K4-L3B).

Evaluates 5 conversational benchmark queries against the Shopee e-commerce corpus,
applying metadata filtering ('buyer' / 'seller') and comparing retrieval results against Gold Answers.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from src.agent import KnowledgeBaseAgent
from src.chunking import FixedSizeChunker, HeadingChunker, RecursiveChunker, SentenceChunker
from src.embeddings import _mock_embed
from src.models import Document
from src.store import EmbeddingStore

sys.stdout.reconfigure(encoding="utf-8")

BENCHMARK_QUERIES = [
    {
        "id": 1,
        "query": "Đơn của mình báo giao thành công được hơn 1 tuần rồi nhưng hôm nay mới phát hiện sản phẩm bị lỗi. Giờ mình còn tạo yêu cầu trả hàng trên Shopee được không?",
        "filter": {"audience": "buyer"},
        "gold_answer": "Nếu đơn thường đã giao quá 7 ngày thì không thể tạo yêu cầu trả hàng trên app. Tuy nhiên nếu là đơn Shopee Mall thì thời hạn trả hàng là 15 ngày nên vẫn còn tạo yêu cầu được.",
        "expected_docs": ["shopee-buyer-return-conditions", "shopee-mall-return-policy", "shopee-buyer-refund-timeline"],
    },
    {
        "id": 2,
        "query": "Khách trả đơn về nhưng lúc shop mở kiện thì thấy thiếu phụ kiện và sản phẩm còn bị vỡ. Shop cần chuẩn bị gì để Shopee xem xét khiếu nại?",
        "filter": {"audience": "seller"},
        "gold_answer": "Shop cần chuẩn bị video mở gói hàng hoàn (rõ mã vận đơn và 6 mặt kiện hàng), ảnh chụp sản phẩm bị vỡ/thiếu và gửi khiếu nại tới Shopee trong vòng 3 ngày kể từ khi nhận hàng.",
        "expected_docs": ["shopee-seller-dispute-response", "shopee-return-evidence-requirements"],
    },
    {
        "id": 3,
        "query": "Mình thanh toán một đơn bằng ShopeePay, đơn khác bằng thẻ Visa. Nếu cả hai được chấp nhận hoàn tiền thì tiền sẽ về đâu và có về cùng lúc không?",
        "filter": {"audience": "buyer"},
        "gold_answer": "Đơn ShopeePay tiền sẽ hoàn về Ví ShopeePay trong vòng 24 giờ. Đơn Visa tiền hoàn về tài khoản thẻ trong 7-14 ngày làm việc. Hai đơn hoàn về hai nơi khác nhau và không cùng lúc.",
        "expected_docs": ["shopee-buyer-refund-timeline", "shopee-buyer-return-conditions", "shopee-mall-return-policy"],
    },
    {
        "id": 4,
        "query": "Mình mua tai nghe, đã bóc seal và dùng thử nhưng thấy không hợp nên muốn trả lại. Nếu chỉ là mình đổi ý thì Shopee có nhận trả không? Những loại hàng nào cũng bị hạn chế kiểu này?",
        "filter": {"audience": "buyer"},
        "gold_answer": "Hàng điện tử/tai nghe đã bóc seal/dùng thử sẽ KHÔNG được trả lại vì lý do đổi ý (chỉ đổi trả nếu có lỗi nhà sản xuất). Các loại hàng thực phẩm tươi sống, đồ lót, dịch vụ điện tử cũng bị hạn chế đổi ý.",
        "expected_docs": ["shopee-buyer-return-shipping-guide", "shopee-buyer-return-conditions", "shopee-product-warranty-policy"],
    },
    {
        "id": 5,
        "query": "Shop đã gửi lại hàng theo đúng quy trình sau khi khách trả đơn, nhưng kiện hàng bị thất lạc trong lúc bên vận chuyển xử lý. Shop có bị mất cả hàng lẫn tiền không, và Shopee giải quyết trường hợp này như thế nào?",
        "filter": {"audience": "seller"},
        "gold_answer": "Shop KHÔNG bị mất tiền. Shopee sẽ làm việc với đơn vị vận chuyển để xác minh việc thất lạc và tiến hành hoàn tiền/đền bù cho Shop theo giá trị hàng hóa quy định trong vòng 7-10 ngày làm việc.",
        "expected_docs": ["shopee-seller-return-appeals", "shopee-seller-dispute-response"],
    },
]


def parse_markdown_file(file_path: Path) -> tuple[dict[str, Any], str]:
    """Separate frontmatter metadata from content body."""
    raw_text = file_path.read_text(encoding="utf-8")
    metadata: dict[str, Any] = {}
    content = raw_text

    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            content = parts[2].strip()
            matches = re.findall(r'^(\w+):\s*"?([^"\n]+)"?$', fm_text, re.M)
            metadata = {k: v.strip() for k, v in matches}

    return metadata, content


def load_and_chunk_corpus(data_dir: Path, chunker: Any) -> list[Document]:
    """Chunk content body and construct Document objects with inherited metadata."""
    chunk_docs: list[Document] = []
    md_files = sorted(data_dir.glob("*.md"))

    for file_path in md_files:
        doc_id = file_path.stem
        frontmatter, content = parse_markdown_file(file_path)
        chunks = chunker.chunk(content)

        for idx, chunk_text in enumerate(chunks):
            chunk_doc = Document(
                id=f"{doc_id}#{idx}",
                content=chunk_text,
                metadata={
                    **frontmatter,
                    "doc_id": doc_id,
                    "chunk_index": idx,
                    "source_file": file_path.name,
                },
            )
            chunk_docs.append(chunk_doc)

    return chunk_docs


def mock_llm(prompt: str) -> str:
    """RAG agent prompt formatter for demo display."""
    return f"[RAG Agent Response] Inferred from retrieved policy docs context."


def run_benchmark(data_dir_name: str = "data/shopee", strategy_name: str = "heading") -> int:
    data_dir = Path(data_dir_name)
    if not data_dir.exists():
        data_dir = Path("data/ecommerce")
        if not data_dir.exists():
            data_dir = Path("data")

    print(f"============================================================")
    print(f"=== CHECKPOINT 5: BENCHMARK & GOLDENSET EVALUATION SUITE ===")
    print(f"============================================================")
    print(f"Corpus Directory : {data_dir}")
    print(f"Strategy Selected: {strategy_name.upper()}")

    # Select chunker strategy
    if strategy_name == "heading":
        chunker = HeadingChunker(chunk_size=500)
    elif strategy_name == "sentence":
        chunker = SentenceChunker(max_sentences_per_chunk=3)
    elif strategy_name == "fixed":
        chunker = FixedSizeChunker(chunk_size=500, overlap=50)
    else:
        chunker = RecursiveChunker(chunk_size=500)

    documents = load_and_chunk_corpus(data_dir, chunker)
    print(f"Total Chunks Loaded: {len(documents)}")

    store = EmbeddingStore(collection_name="benchmark_store", embedding_fn=_mock_embed)
    store.add_documents(documents)
    print(f"EmbeddingStore Collection Size: {store.get_collection_size()}\n")

    agent = KnowledgeBaseAgent(store=store, llm_fn=mock_llm)

    eval_summary = []

    print("=== BENCHMARK QUERY EVALUATION ===")
    for q in BENCHMARK_QUERIES:
        query_text = q["query"]
        meta_filter = q["filter"]
        gold_ans = q["gold_answer"]
        expected_docs = q["expected_docs"]

        print(f"\nQuery #{q['id']}: '{query_text}'")
        print(f"  Filter Applied: {meta_filter}")
        print(f"  Gold Answer   : {gold_ans}")

        if meta_filter:
            results = store.search_with_filter(query_text, top_k=3, metadata_filter=meta_filter)
        else:
            results = store.search(query_text, top_k=3)

        retrieved_docs = [r.get("metadata", {}).get("doc_id", "").split("#")[0] for r in results]
        match_in_top1 = retrieved_docs[0] in expected_docs if retrieved_docs else False
        match_in_top3 = any(d in expected_docs for d in retrieved_docs)

        print("  Top-3 Retrieved Chunks:")
        for idx, res in enumerate(results, start=1):
            src = res.get("metadata", {}).get("doc_id", "unknown")
            snippet = res.get("content", "").replace("\n", " ")[:90]
            print(f"    [{idx}] score={res['score']:.4f} | doc_id={src} | content={snippet}...")

        answer = agent.answer(query_text, top_k=3)
        print(f"  Agent Answer  : {answer}")
        print(f"  Relevance Status: Top-1 Match={'YES' if match_in_top1 else 'NO'} | Top-3 Match={'YES' if match_in_top3 else 'NO'}")

        eval_summary.append({
            "id": q["id"],
            "filter": meta_filter.get("audience", "none"),
            "top1_doc": retrieved_docs[0] if retrieved_docs else "none",
            "top1_match": match_in_top1,
            "top3_match": match_in_top3,
            "score": 2.0 if match_in_top1 else (1.0 if match_in_top3 else 0.0)
        })

    # Summary Table
    print("\n" + "="*70)
    print("=== FINAL BENCHMARK SUMMARY & SCORE EVALUATION ===")
    print("="*70)
    print(f"{'#':<3} | {'Filter':<7} | {'Top-1 Retrived Doc':<38} | {'Top-1 Match':<11} | {'Score'}")
    print("-" * 70)
    total_score = 0.0
    for item in eval_summary:
        total_score += item["score"]
        match_str = "PASSED" if item["top1_match"] else "PARTIAL"
        print(f"{item['id']:<3} | {item['filter']:<7} | {item['top1_doc']:<38} | {match_str:<11} | {item['score']:.1f}/2.0")

    print("-" * 70)
    print(f"TOTAL BENCHMARK RETRIEVAL SCORE: {total_score:.1f} / 10.0 ({total_score*10:.0f}%)")
    print("============================================================\n")

    return 0


if __name__ == "__main__":
    strategy = sys.argv[1].lower() if len(sys.argv) > 1 else "heading"
    sys.exit(run_benchmark(strategy_name=strategy))
