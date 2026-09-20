# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Enigma - L3B
**Thành viên & Phân vai (4 người):**
1. **Nguyễn Anh Tuấn (MSV: 2A202602700)** — Teamlead | Vai R4: Report & Demo Lead (Điều phối dự án, Flow, Prototype, Backend, UXUI, gom kết quả và dẫn thuyết trình demo)
2. **Đặng Quang Hưng (MSV: 2A202602719)** — Member | Vai R3: Strategy Lead (Mining evidence, chunk theo heading `HeadingChunker`, chạy baseline nhóm)
3. **Nguyễn Hữu Thành (MSV: 2A202602813)** — Member | Vai R1: Data Lead (AI Engineer, Track AI & dữ liệu, kiểm tra metadata, quản lý `sources.csv`)
4. **Hà Thị Mỹ Linh (MSV: 2A202602619)** — BA | Vai R2: Benchmark Lead (Track chính về tìm hiểu thị trường & nghiệp vụ, soạn 5 query + gold answer)

**Ngày:** 20/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chia vai (5 phút)

Nhóm 4 người, mỗi người một vai. Vai là trách nhiệm điều phối cộng thêm — ai cũng vẫn tự code Giai đoạn 2 và tự chạy benchmark riêng.

| Vai | Thành viên | Mã sinh viên (MSV) | Vai trò trong nhóm | Trách nhiệm điều phối & thực thi Lab 7 | Hạn |
|-----|------------|--------------------|--------------------|----------------------------------------|-----|
| **R1 · Data** | **Nguyễn Hữu Thành** | `2A202602813` | Member (AI Engineer) | Track AI và dữ liệu: Chốt chủ đề Shopee, chia mỗi người 2–3 URL, kiểm metadata từng file, giữ `sources.csv` | CP2 |
| **R2 · Benchmark** | **Hà Thị Mỹ Linh** | `2A202602619` | BA | Track chính về tìm hiểu thị trường: Viết 5 query + gold answer, tự kiểm mỗi gold answer trích được từ tài liệu thật | CP5 |
| **R3 · Strategy** | **Đặng Quang Hưng** | `2A202602719` | Member (Strategy) | Mining evidence, lập evidence table, bảo đảm không ai trùng chiến lược, nhận vai chunk theo heading (`HeadingChunker`), chạy baseline cho nhóm | CP5 |
| **R4 · Report & Demo Lead** | **Nguyễn Anh Tuấn** | `2A202602700` | Teamlead | Điều phối dự án, phân chia công việc, tạo Flow, Prototype, Backend, UXUI, gom kết quả cả nhóm và dẫn phần thuyết trình demo | Demo |

> **Quy định chiến lược:** Chiến lược chunking không được trùng nhau.
> - Thành viên 1 (R1): `FixedSizeChunker` (có overlap) — Nguyễn Hữu Thành
> - Thành viên 2 (R2): `RecursiveChunker` — Hà Thị Mỹ Linh
> - Thành viên 3 (R3): Chunker theo heading (`HeadingChunker`) — **vai thứ ba là bắt buộc** (Đặng Quang Hưng đảm nhiệm).
> - Thành viên 4 (R4): `SentenceChunker` (ngắt theo câu trọn vẹn) — Nguyễn Anh Tuấn

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách Đổi trả, Hoàn tiền và Quy định người mua/người bán trên sàn thương mại điện tử Shopee (Shopee Vietnam Help Center).

**Tại sao nhóm chọn chủ đề này?**
> Shopee là sàn thương mại điện tử phổ biến nhất tại Việt Nam với lượng giao dịch lớn. Các điều khoản đổi trả, bảo hành, hủy đơn và khiếu nại có cấu trúc điều khoản rõ ràng nhưng áp dụng quy định khác nhau đối với từng đối tượng (Người mua `buyer` vs Người bán `seller`), tạo bài toán thực tế lý tưởng để đánh giá khả năng truy xuất RAG và lọc bằng siêu dữ liệu (`metadata_filter`).

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Điều kiện Trả hàng và Hoàn tiền Shopee | https://help.shopee.vn/portal/4/article/77251 | 2026-09-20 / 2026-v1 | ~26,400 | `audience: buyer`, `category: return-refund` |
| 2 | Quy định Trả hàng Hoàn tiền cho Shopee Mall | https://help.shopee.vn/portal/4/article/188931 | 2026-09-20 / 2026-v1 | ~9,000 | `audience: buyer`, `category: return-refund-mall` |
| 3 | Hướng dẫn Yêu cầu Trả hàng Hoàn tiền cho Người mua | https://help.shopee.vn/portal/4/article/79233 | 2026-09-20 / 2026-v1 | ~3,700 | `audience: buyer`, `category: return-request` |
| 4 | Thời gian xử lý và Hoàn tiền cho Người mua | https://help.shopee.vn/portal/4/article/79467 | 2026-09-20 / 2026-v1 | ~4,900 | `audience: buyer`, `category: payment-refund` |
| 5 | Hướng dẫn Người bán xử lý khiếu nại Trả hàng | https://help.shopee.vn/portal/4/article/190242 | 2026-09-20 / 2026-v1 | ~11,300 | `audience: seller`, `category: seller-dispute` |
| 6 | Hướng dẫn Người bán khiếu nại quyết định Trả hàng | https://help.shopee.vn/portal/4/article/189477 | 2026-09-20 / 2026-v1 | ~8,300 | `audience: seller`, `category: seller-dispute` |
| 7 | Quy định đóng gói và gửi hàng trả về cho Người mua | https://help.shopee.vn/portal/4/article/204305 | 2026-09-20 / 2026-v1 | ~10,300 | `audience: buyer`, `category: return-shipping` |
| 8 | Điều kiện và Thời hạn bảo hành sản phẩm | https://help.shopee.vn/portal/4/article/79182 | 2026-09-20 / 2026-v1 | ~3,300 | `audience: buyer`, `category: warranty` |
| 9 | Quy định về Bằng chứng Trả hàng Hoàn tiền | https://help.shopee.vn/portal/4/article/77265 | 2026-09-20 / 2026-v1 | ~6,700 | `audience: both`, `category: return-evidence` |
| 10 | Chính sách Hủy đơn hàng cho Người mua và Người bán | https://help.shopee.vn/portal/4/article/77250 | 2026-09-20 / 2026-v1 | ~33,300 | `audience: both`, `category: cancellation` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | String | `shopee-buyer-return-conditions` | Định danh duy nhất của tài liệu để truy vết và xóa chunk. |
| `title` | String | `Điều kiện Trả hàng và Hoàn tiền Shopee` | Tên tiêu đề đầy đủ hiển thị cho người dùng / RAG context. |
| `source_url` | String | `https://help.shopee.vn/portal/4/article/77251` | URL gốc phục vụ kiểm chứng câu trả lời của RAG Agent. |
| `retrieved_at` | String | `2026-09-20` | Kiểm soát ngày thu thập dữ liệu (độ mới). |
| `document_version` | String | `2026-v1` | Quản lý phiên bản quy định theo thời gian. |
| `audience` | String | `buyer` / `seller` / `both` | **Cốt lõi cho `metadata_filter`**: Lọc chính xác quy định áp dụng cho Người mua hay Người bán. |
| `category` | String | `return-refund` / `seller-dispute` / `warranty` | Phân loại phân mảng nội dung chính sách để thu hẹp không gian tìm kiếm. |
| `language` | String | `vi` | Phân loại ngôn ngữ của tài liệu. |
| `license_or_permission` | String | `public-source` | Xác minh nguồn dữ liệu mở công khai được phép trích xuất. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên các tài liệu đã loại bỏ YAML frontmatter:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| `shopee-buyer-return-conditions.md` | FixedSizeChunker (`fixed_size`) | 41 | 498.0 ký tự | Khá kém, dễ cắt ngang câu điều khoản. |
| `shopee-buyer-return-conditions.md` | SentenceChunker (`by_sentences`) | 48 | 405.8 ký tự | Tốt, giữ trọn vẹn từng câu quy định. |
| `shopee-buyer-return-conditions.md` | RecursiveChunker (`recursive`) | 133 | 145.6 ký tự | Ngắt nhỏ theo xuống dòng, giữ được tiêu đề ngắn. |
| `shopee-mall-return-policy.md` | FixedSizeChunker (`fixed_size`) | 14 | 470.1 ký tự | Giới hạn ký tự cố định 500, cắt đôi quy trình. |
| `shopee-mall-return-policy.md` | SentenceChunker (`by_sentences`) | 10 | 626.9 ký tự | Gom nhóm câu tốt nhưng chunk hơi dài. |
| `shopee-mall-return-policy.md` | RecursiveChunker (`recursive`) | 112 | 54.4 ký tự | Chunk quá vụn do ngắt đệ quy theo các dòng trống. |

### Chiến lược của từng thành viên (4 Chiến Lược Không Trùng Nhau)

**Thành viên 1 — R1: Nguyễn Hữu Thành (MSV: 2A202602813) — Data Lead**
- **Loại chiến lược:** `FixedSizeChunker` (chunk_size=500, overlap=50)
- **Mô tả & lý do chọn:** Đơn giản, đảm bảo độ dài các chunk đồng đều. Thêm overlap 50 ký tự để hạn chế việc ngắt quãng ý nghĩa giữa 2 chunk kề nhau.

**Thành viên 2 — R2: Hà Thị Mỹ Linh (MSV: 2A202602619) — Benchmark Lead**
- **Loại chiến lược:** `RecursiveChunker` (chunk_size=500, separators=["\n\n", "\n", ". ", " "])
- **Mô tả & lý do chọn:** Thử nghiệm ngắt theo cấu trúc đoạn văn trước (`\n\n`), nếu đoạn văn vượt quá 500 ký tự mới tiếp tục hạ bậc xuống câu và từ. Phù hợp với văn bản điều khoản có phân đoạn rõ rệt.

**Thành viên 3 — R3: Đặng Quang Hưng (MSV: 2A202602719) — Strategy Lead (Bắt buộc)**
- **Loại chiến lược:** `HeadingChunker` (Chiến lược ngắt theo Tiêu đề Markdown `#`, `##`, `###`)
- **Mô tả & lý do chọn:** Phù hợp tuyệt đối với văn bản pháp lý / điều khoản của Shopee được tổ chức theo từng Điều/Mục. Mỗi Section tiêu đề được ngắt thành 1 chunk trọn vẹn. Khi một Section quá dài (>500 ký tự), đệ quy ngắt nhỏ và **gắn lại Tiêu đề gốc vào đầu từng mảnh con** để bảo toàn ngữ cảnh.
- **Code snippet (custom `HeadingChunker`):**
```python
class HeadingChunker:
    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size
        self._recursive = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []
        sections = [s.strip() for s in re.split(r"(?=(?:^|\n)#{1,6}\s+)", text) if s.strip()]
        chunks = []
        for section in sections:
            if len(section) <= self.chunk_size:
                chunks.append(section)
            else:
                lines = section.split("\n", 1)
                heading = lines[0] if lines[0].startswith("#") else ""
                body = lines[1] if len(lines) > 1 else section
                for sub in self._recursive.chunk(body):
                    chunks.append(f"{heading}\n{sub}" if heading and not sub.startswith("#") else sub)
        return chunks
```

**Thành viên 4 — R4: Nguyễn Anh Tuấn (MSV: 2A202602700) — Report & Demo Lead**
- **Loại chiến lược:** `SentenceChunker` (max_sentences_per_chunk=3)
- **Mô tả & lý do chọn:** Nhóm các câu hoàn chỉnh dựa trên dấu kết thúc câu (`.`, `!`, `?`). Bảo đảm ngữ pháp câu văn trọn vẹn và không bị đứt gãy từ ngữ khi đưa vào Prompt của LLM.

### So Sánh Giữa Các Thành Viên

| Thành viên | MSV | Vai trò | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|------------|-----|---------|----------------------|----------------------|-----------|----------|
| **Nguyễn Hữu Thành** | `2A202602813` | R1 · Data | `FixedSizeChunker` | 7.0 / 10 | Tốc độ xử lý nhanh, kích thước chunk đồng đều. | Dễ bị cắt ngang câu điều khoản quan trọng. |
| **Hà Thị Mỹ Linh** | `2A202602619` | R2 · Benchmark | `RecursiveChunker` | 8.5 / 10 | Giữ trọn cấu trúc đoạn văn bản `\n\n`. | Đôi khi tạo ra các chunk quá ngắn khi văn bản có nhiều dòng trống. |
| **Đặng Quang Hưng** | `2A202602719` | R3 · Strategy | `HeadingChunker` (Heading) | 9.5 / 10 | **Tối ưu nhất**: Bảo toàn 100% ngữ cảnh tiêu đề cho từng mảnh con. | Cần cài đặt custom logic phân tách tiêu đề phức tạp hơn. |
| **Nguyễn Anh Tuấn** | `2A202602700` | R4 · Report & Demo | `SentenceChunker` | 8.0 / 10 | Đảm bảo ngữ pháp từng câu văn hoàn chỉnh, dễ đọc. | Kích thước chunk không đồng đều phụ thuộc vào câu dài hay ngắn. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> **`HeadingChunker` (Chia nhỏ theo Tiêu đề/Heading)** là chiến lược tối ưu nhất cho văn bản chính sách thương mại điện tử. Lý do là các quy định Shopee được trình bày theo từng Điều/Mục rõ ràng; việc giữ tiêu đề mục ở đầu mỗi chunk giúp véc-tơ embedding định vị chính xác ngữ cảnh quy định ngay cả khi văn bản bị chia nhỏ.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Đơn của mình báo giao thành công được hơn 1 tuần rồi nhưng hôm nay mới phát hiện sản phẩm bị lỗi. Giờ mình còn tạo yêu cầu trả hàng trên Shopee được không? (`filter: audience=buyer`) | Nếu đơn thường đã giao quá 7 ngày thì không thể tạo yêu cầu trả hàng trên ứng dụng. Tuy nhiên nếu là đơn Shopee Mall thì thời hạn trả hàng là 15 ngày nên vẫn còn tạo yêu cầu được. | `shopee-buyer-return-conditions.md` / `shopee-mall-return-policy.md` |
| 2 | Khách trả đơn về nhưng lúc shop mở kiện thì thấy thiếu phụ kiện và sản phẩm còn bị vỡ. Shop cần chuẩn bị gì để Shopee xem xét khiếu nại? (`filter: audience=seller`) | Shop cần chuẩn bị video mở gói hàng hoàn (rõ mã vận đơn và 6 mặt kiện hàng), ảnh chụp sản phẩm bị vỡ/thiếu và gửi khiếu nại tới Shopee trong vòng 3 ngày kể từ khi nhận hàng. | `shopee-seller-dispute-response.md` / `shopee-return-evidence-requirements.md` |
| 3 | Mình thanh toán một đơn bằng ShopeePay, đơn khác bằng thẻ Visa. Nếu cả hai được chấp nhận hoàn tiền thì tiền sẽ về đâu và có về cùng lúc không? (`filter: audience=buyer`) | Đơn ShopeePay tiền sẽ hoàn về Ví ShopeePay trong vòng 24 giờ. Đơn Visa tiền hoàn về tài khoản thẻ trong 7-14 ngày làm việc. Hai đơn hoàn về hai nơi khác nhau và không cùng lúc. | `shopee-buyer-refund-timeline.md` |
| 4 | Mình mua tai nghe, đã bóc seal và dùng thử nhưng thấy không hợp nên muốn trả lại. Nếu chỉ là mình đổi ý thì Shopee có nhận trả không? Những loại hàng nào cũng bị hạn chế kiểu này? (`filter: audience=buyer`) | Hàng điện tử đã bóc seal/dùng thử sẽ KHÔNG được trả lại vì lý do đổi ý (chỉ đổi trả nếu có lỗi nhà sản xuất). Các loại hàng thực phẩm tươi sống, đồ lót, dịch vụ điện tử cũng bị hạn chế đổi ý. | `shopee-buyer-return-conditions.md` / `shopee-product-warranty-policy.md` |
| 5 | Shop đã gửi lại hàng theo đúng quy trình sau khi khách trả đơn, nhưng kiện hàng bị thất lạc trong lúc bên vận chuyển xử lý. Shop có bị mất cả hàng lẫn tiền không, và Shopee giải quyết trường hợp này như thế nào? (`filter: audience=seller`) | Shop KHÔNG bị mất tiền. Shopee sẽ làm việc với đơn vị vận chuyển để xác minh việc thất lạc và tiến hành hoàn tiền/đền bù cho Shop theo giá trị hàng hóa quy định trong vòng 7-10 ngày làm việc. | `shopee-seller-return-appeals.md` |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Hạn trả hàng quá 1 tuần (Lọc `buyer`) | `search_with_filter` + `Heading` | Có (Top-1) | Lọc chính xác điều kiện 7 ngày vs 15 ngày Mall |
| 2 | Shop khiếu nại hàng hoàn vỡ/thiếu (Lọc `seller`) | `search_with_filter` + `Heading` | Có (Top-1) | Lọc đúng quy trình khiếu nại của Người bán |
| 3 | Hoàn tiền ShopeePay vs Thẻ Visa (Lọc `buyer`) | `by_sentences` / `Heading` | Có (Top-1) | Trích xuất thời hạn 24h vs 7-14 ngày |
| 4 | Trả hàng bóc seal do đổi ý (Lọc `buyer`) | `HeadingChunker` | Có (Top-1) | Tìm thấy danh mục cấm đổi ý khi đã dùng |
| 5 | Thất lạc hàng hoàn khi vận chuyển (Lọc `seller`) | `search_with_filter` + `Heading` | Có (Top-1) | Lọc đúng quy định đền bù vận chuyển cho Shop |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Lọc bằng metadata (`search_with_filter`) phát huy tác dụng vượt trội ở **Câu hỏi #1, #2 và #5**. Nhờ pre-filtering `audience: "buyer"` hoặc `audience: "seller"`, RAG agent không bị lẫn lộn giữa góc nhìn của Người mua và Người bán trong các câu hỏi tình huống thực tế phức tạp.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. Pre-filtering theo Metadata (`audience`) giải quyết triệt để vấn đề nhiễu ngữ cảnh giữa Người mua và Người bán trong RAG TMĐT.
> 2. Kỹ thuật `HeadingChunker` gắn lại tiêu đề Markdown vào đầu mỗi mảnh con giúp tăng điểm cosine similarity đáng kể khi tra cứu các điều khoản luật/quy định.
> 3. Đánh giá sự khác biệt giữa véc-tơ embedding cơ bản (Mock / Baseline) và việc xử lý các từ ngữ mang tính phủ định trong câu hỏi tự nhiên.
> 4. **Cơ chế Out-of-Domain Guardrail**: Tự động phát hiện và từ chối trả lời các câu hỏi không liên quan đến chính sách Shopee (thời tiết, ẩm thực, địa lý...), bảo vệ hệ thống khỏi hiện tượng sinh ảo giác (hallucination).

### Kịch Bản Thuyết Trình Demo (`demo.py`)
> Nhóm chuẩn bị sẵn công cụ demo đa chế độ tại [`demo.py`](file:///d:/University/AICB/Phase1/D7/K4-L3B-Data-Foundations-DangQuangHung-02719/demo.py):
> - **Phần 1 — Trình diễn 5 câu hỏi Benchmark chuẩn:** Cho thấy hiệu quả của bộ lọc `audience` (`buyer` vs `seller`) trên 10 tài liệu chính sách Shopee, truy xuất trúng điều khoản trọng tâm.
> - **Phần 2 — Trình diễn Guardrail từ chối câu hỏi lạc đề:** Thử nghiệm với các câu hỏi ngoài phạm vi (như *"Thủ đô nước Pháp"*, *"Cách nấu phở bò"*, *"Thời tiết ngày mai"*), hệ thống phát hiện nằm ngoài miền nghiệp vụ và từ chối trả lời một cách chuẩn mực.
> - **Phần 3 — Chế độ Live Interactive Chat (`python demo.py -i`):** Cho phép giảng viên/hội đồng nhập câu hỏi bất kỳ từ bàn phím để kiểm chứng trực tiếp tính đúng đắn và khả năng lọc.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một bộ tài liệu nhưng nếu chia nhỏ theo kích thước cố định (`FixedSizeChunker`), các quy định pháp lý rất dễ bị cắt đứt nửa chừng gây mất ý nghĩa. Ngược lại, chiến lược `HeadingChunker` bảo toàn được cấu trúc phân cấp điều khoản, giúp Agent trả lời chính xác hơn.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nếu làm lại, nhóm sẽ bổ sung thêm các trường metadata chi tiết hơn như `sub_category` (`electronics`, `food`, `fashion`) để tăng khả năng tiền lọc chính xác cho các nhóm hàng hóa đặc thù. Ngoài ra, nhóm sẽ thử nghiệm mô hình Dense Embedding thực tế (như `text-embedding-3` hoặc `multilingual-e5`) thay vì véc-tơ mock để cải thiện độ tương đồng ngữ nghĩa đối với các câu hỏi có chứa cấu trúc phủ định phức tạp.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |

