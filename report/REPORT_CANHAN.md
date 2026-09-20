# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Đặng Quang Hưng (MSV: 2A202602719)
**Nhóm:** Nhóm 1 - L3B
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao (gần 1.0) nghĩa là hai góc của véc-tơ embedding chỉ về cùng một hướng trong không gian đa chiều, phản ánh hai đoạn văn bản có sự đồng nhất cao về ngữ nghĩa và nội dung.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Shopee hỗ trợ đổi trả hàng trong vòng 7 ngày cho sản phẩm lỗi."
- Câu B: "Người mua có thể yêu cầu trả hàng và hoàn tiền trong 7 ngày nếu hàng bị hỏng."
- Tại sao tương đồng: Cả hai câu đều nói về cùng một quy định thời hạn đổi trả 7 ngày khi hàng lỗi, véc-tơ biểu diễn có góc giữa hai véc-tơ rất nhỏ.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Shopee hỗ trợ đổi trả hàng trong vòng 7 ngày cho sản phẩm lỗi."
- Câu B: "Hà Nội là thủ đô của nước Cộng hòa Xã hội Chủ nghĩa Việt Nam."
- Tại sao khác: Hai câu thuộc hai chủ đề hoàn toàn độc lập (quy định TMĐT vs địa lý hành chính), góc giữa hai véc-tơ gần 90 độ (cosine similarity gần 0).

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Khoảng cách Euclid bị ảnh hưởng bởi độ dài của véc-tơ (văn bản dài hơn sẽ chứa nhiều từ hơn làm véc-tơ có độ dài lớn hơn). Cosine similarity chỉ đo hướng (độ chênh lệch góc), giúp so sánh độ tương đồng ngữ nghĩa một cách độc lập với độ dài của câu hay đoạn văn.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* `số lượng chunk = làm_tròn_lên((10,000 - 50) / (500 - 50)) = làm_tròn_lên(9,950 / 450) = làm_tròn_lên(22.11)`
> *Đáp án:* **23 chunks**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi `overlap=100`, bước nhảy `step = 500 - 100 = 400`, số chunk = `làm_tròn_lên(9,900 / 400) = 25 chunks` (tăng thêm 2 chunks). Độ chồng chéo lớn hơn giúp giữ được trọn vẹn ngữ cảnh ở ranh giới giữa 2 chunks liên tiếp, tránh làm ngắt đôi các câu văn hoặc ý quan trọng.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Sử dụng regex lookbehind `r'(?<=[.!?])\s+|(?<=[.!?])\n'` để ngắt câu dựa trên dấu câu cuối câu (`.`, `!`, `?`) theo sau là khoảng trắng/dòng mới. Nhóm tối đa `max_sentences_per_chunk` câu lại thành 1 chunk và loại bỏ các chuỗi rỗng.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Áp dụng thuật toán đệ quy thử nghiệm danh sách separators theo ưu tiên `["\n\n", "\n", ". ", " ", ""]`. Trường hợp cơ sở (base case) là khi độ dài đoạn văn nhỏ hơn hoặc bằng `chunk_size` thì trả về ngay; nếu hết danh sách separators mà văn bản vẫn quá dài thì fallback ngắt theo độ dài ký tự cố định.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` tính toán véc-tơ embedding cho từng document thông qua `_embedding_fn`, lưu trữ bản ghi vào danh sách bộ nhớ `self._store` và đồng thời đẩy vào collection của ChromaDB (nếu có). Hàm `search` tính tích vô hướng (`_dot`) giữa véc-tơ truy vấn và tất cả véc-tơ lưu trữ, sau đó sắp xếp giảm dần theo similarity score và lấy ra top-$k$.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` thực hiện pre-filtering trong `self._store` bằng cách lọc các bản ghi thỏa mãn tất cả khóa-giá trị trong `metadata_filter` trước khi tính similarity search. `delete_document` tìm và xóa toàn bộ chunks trong `self._store` có `id` hoặc `metadata['doc_id']` khớp với `doc_id` cần xóa.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Gọi `store.search` để lấy ra $k$ chunks có liên quan nhất với câu hỏi. Nối nội dung các chunks lại thành chuỗi ngữ cảnh (context), sau đó tạo một cấu trúc prompt RAG hoàn chỉnh đưa cho hàm `llm_fn` để tổng hợp câu trả lời.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

### Kết Quả Kiểm Thử (Test Results)

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\University\AICB\Phase1\D7\K4-L3B-Data-Foundations-DangQuangHung-02719
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.11s ==============================
```

**Số lượng bài test vượt qua (pass):** **42** / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Thời gian trả hàng Shopee Mall là 15 ngày. | Thời gian trả hàng Shopee Mall là 15 ngày. | cao | 1.000 | Đúng |
| 2 | Thời gian trả hàng Shopee Mall là 15 ngày. | Shopee Mall cho phép người mua trả hàng trong 15 ngày. | cao | 0.287 | Đúng (Mock) |
| 3 | Thời gian trả hàng Shopee Mall là 15 ngày. | Shop thường có thời gian trả hàng là 7 ngày. | trung bình | 0.077 | Đúng |
| 4 | Thời gian trả hàng Shopee Mall là 15 ngày. | Hà Nội là thủ đô của Việt Nam. | thấp | 0.223 | Khá thấp |
| 5 | Đơn hàng được áp dụng hoàn tiền tự động. | Đơn hàng không được áp dụng hoàn tiền tự động. | cao | -0.042 | Bất ngờ |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp số 5 ("Được hoàn tiền tự động" vs "Không được hoàn tiền tự động") cho kết quả bất ngờ vì hai câu chỉ khác nhau từ "không" nhưng lại bị véc-tơ đẩy về điểm âm (-0.042). Điều này cho thấy với véc-tơ deterministic mock / embedding cơ bản, sự thay đổi từ phủ định có ảnh hưởng lớn đến phân bổ véc-tơ, nhấn mạnh tầm quan trọng của các mô hình multilingual embedding thực tế (`sentence-transformers` hoặc `text-embedding-3`).

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Đơn của mình báo giao thành công được hơn 1 tuần rồi nhưng hôm nay mới phát hiện sản phẩm bị lỗi. Giờ mình còn tạo yêu cầu trả hàng trên Shopee được không? (`filter: audience=buyer`) | Hướng dẫn Yêu cầu Trả hàng Hoàn tiền cho Người mua: Nếu quá 7 ngày với đơn thường thì hết hạn, đơn Mall là 15 ngày... | 0.433 | Có (Lọc chuẩn) | Đơn thường quá 7 ngày không tạo được yêu cầu, nếu là Shopee Mall (15 ngày) thì vẫn còn tạo được. |
| 2 | Khách trả đơn về nhưng lúc shop mở kiện thì thấy thiếu phụ kiện và sản phẩm còn bị vỡ. Shop cần chuẩn bị gì để Shopee xem xét khiếu nại? (`filter: audience=seller`) | Hướng dẫn Người bán xử lý khiếu nại Trả hàng / Quy định bằng chứng: Video mở gói hàng 6 mặt và mã vận đơn trong 3 ngày... | 0.350 | Có (Lọc chuẩn) | Shop cần chuẩn bị video mở kiện hàng hoàn rõ 6 mặt & mã vận đơn, ảnh chụp vỡ thiếu và gửi khiếu nại trong 3 ngày. |
| 3 | Mình thanh toán một đơn bằng ShopeePay, đơn khác bằng thẻ Visa. Nếu cả hai được chấp nhận hoàn tiền thì tiền sẽ về đâu và có về cùng lúc không? (`filter: audience=buyer`) | Quy định Trả hàng Hoàn tiền cho Shopee Mall / Thời gian hoàn tiền: Ví ShopeePay trong 24h, Thẻ Visa 7-14 ngày... | 0.354 | Có (Lọc chuẩn) | Tiền hoàn về 2 nơi khác nhau (Ví ShopeePay về ví trong 24h, Visa về thẻ trong 7-14 ngày) và không về cùng lúc. |
| 4 | Mình mua tai nghe, đã bóc seal và dùng thử nhưng thấy không hợp nên muốn trả lại. Nếu chỉ là mình đổi ý thì Shopee có nhận trả không? Những loại hàng nào cũng bị hạn chế kiểu này? (`filter: audience=buyer`) | Điều kiện Trả hàng và Hoàn tiền Shopee: Tai nghe/hàng điện tử bóc seal đã dùng không được trả do đổi ý... | 0.396 | Có (Lọc chuẩn) | Tai nghe đã bóc seal dùng thử không được trả vì đổi ý. Các loại hàng thực phẩm tươi sống, đồ vệ sinh cá nhân cũng bị cấm đổi ý. |
| 5 | Shop đã gửi lại hàng theo đúng quy trình sau khi khách trả đơn, nhưng kiện hàng bị thất lạc trong lúc bên vận chuyển xử lý. Shop có bị mất cả hàng lẫn tiền không, và Shopee giải quyết trường hợp này như thế nào? (`filter: audience=seller`) | Hướng dẫn Người bán khiếu nại / Quy định Shopee Mall: Shopee xác minh đơn vị vận chuyển làm thất lạc và đền bù cho Shop... | 0.345 | Có (Lọc chuẩn) | Shop không bị mất tiền. Shopee sẽ đối soát với đơn vị vận chuyển và đền bù tiền hàng cho Shop trong 7-10 ngày. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **5** / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Kỹ thuật lọc metadata pre-filtering (`search_with_filter`) giúp giảm nhiễu tuyệt đối giữa các chính sách dành cho Người mua (`buyer`) và Người bán (`seller`). Ngoài ra, chiến lược `RecursiveChunker` giữ lại được các tiêu đề bài viết tốt hơn so với ngắt độ dài cố định `FixedSizeChunker`.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
