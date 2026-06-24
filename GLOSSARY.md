# 📖 Glossary — Bảng tra thuật ngữ nhanh

> Mỗi từ **một dòng** giải thích bằng lời thường. Quên thì tra ở đây.
> Cần hiểu sâu (công thức, lý do) → xem [notes-knowledge.md](notes-knowledge.md).
> **Quy ước:** gặp thuật ngữ mới trong lúc học → thêm 1 dòng vào đây.

---

## 🔍 RAG cơ bản

| Thuật ngữ | Một câu |
|---|---|
| **Embedding** | biến text thành dãy số (vector) để máy so sánh *nghĩa* |
| **Vector** | dãy số (1024 chiều với bge-m3) đại diện nghĩa một đoạn text |
| **Cosine similarity** | đo độ giống về nghĩa bằng *góc* giữa 2 vector (1=giống, 0=không liên quan) |
| **Chunk** | một mẩu văn bản nhỏ cắt ra từ tài liệu dài |
| **Chunking** | việc cắt tài liệu dài thành các chunk |
| **Dense retrieval** | tìm theo *nghĩa* bằng vector (bge-m3) — giỏi ngữ nghĩa, dễ trượt từ khóa chính xác |
| **Sparse retrieval / BM25** | tìm theo *từ khóa* khớp chữ — bắt "SPF 50+", mã SKU, tên riêng |
| **Hybrid search** | chạy cả dense + sparse rồi gộp — lấy điểm mạnh cả hai |
| **RRF** (Reciprocal Rank Fusion) | gộp nhiều bảng xếp hạng thành một, dựa trên *thứ hạng* (không phải điểm tuyệt đối) |
| **Rerank** | chấm lại top-k cho chính xác hơn sau khi retrieve |
| **Cross-encoder** | model đọc query + doc *cùng nhau* trong 1 lượt → chính xác hơn nhưng chậm hơn |
| **Bi-encoder** | encode query và doc *riêng lẻ* rồi so vector → nhanh nhưng kém tinh |
| **top_k** | số kết quả muốn lấy ra |
| **Qdrant** | cơ sở dữ liệu chuyên lưu & tìm vector |
| **bge-m3** | model embedding đang dùng (1024 chiều, 100+ ngôn ngữ) |
| **Payload** | dữ liệu kèm theo mỗi vector trong Qdrant (text gốc, source, tenant_id) |
| **tenant_id / namespace** | nhãn ngăn cách dữ liệu từng niche/kênh — mọi search bắt buộc lọc theo nó |

---

## 🔧 CRAG (việc đang làm)

| Thuật ngữ | Một câu |
|---|---|
| **CRAG** (Corrective RAG) | RAG biết *tự chấm điểm* kết quả retrieval rồi *sửa sai* khi gặp rác |
| **Grade / grading** | hỏi LLM CÓ/KHÔNG: chunk này có thật sự liên quan câu hỏi không |
| **candidates** | mẻ *thô* retriever trả về — chưa ai kiểm, lọc theo *điểm số* |
| **relevant** | các chunk được grade chấm CÓ — lọc theo *chất lượng* |
| **verdict** | kết luận sau grade: CORRECT / AMBIGUOUS / INCORRECT |
| **CORRECT / AMBIGUOUS / INCORRECT** | nhiều / vài / không chunk tốt → dùng luôn / kết hợp / phải tìm lại |
| **Corrective retrieval** | khi gặp rác, tìm lại bằng cách khác (nới top_k, đổi BM25, viết lại query) — Nyxara làm *trong kho local*, không ra web |
| **Retry guard (chốt chặn)** | đếm số lần thử lại (`attempts`); quá ngưỡng thì dừng — tránh lặp vô hạn |
| **In-store correction** | sửa sai bằng cách tìm lại *trong kho local*, không ra internet (luật Nyxara) |
| **Hallucination** | model *bịa* thông tin không có trong nguồn |
| **Grounding** | câu trả lời bám chặt vào nguồn dữ liệu thật, truy được nguồn |
| **LLM-as-judge** | dùng một LLM làm *giám khảo* chấm điểm (vd grader chấm liên quan yes/no) — cùng bộ não, đội mũ "kiểm tra" thay vì "viết" |
| **Abstention** | model tự nói "không biết / chưa có thông tin" thay vì đoán bừa |

---

## 🕹️ LangGraph / Agent

| Thuật ngữ | Một câu |
|---|---|
| **State machine** | máy chạy theo các *trạm* có thứ tự, mỗi trạm xử lý rồi chuyển tiếp |
| **State** | "tờ giấy" dữ liệu chạy qua các trạm — mỗi trạm đọc/ghi vài ô |
| **Node** | một trạm = một *hàm*: nhận state → làm việc → trả về dict phần cần ghi |
| **Edge** | đường nối giữa các node, quyết định đi trạm nào tiếp |
| **Conditional edge** | đường *rẽ nhánh* tùy điều kiện (vd: nhìn verdict mà rẽ) |
| **LangGraph** | framework dựng state machine cho agent — chỉ lo *luồng*, không lo retrieval |
| **Supervisor–Worker** | 1 "sếp" điều phối, nhiều worker mỗi đứa chuyên một việc nhỏ |
| **Critic** | agent kiểm tra chống bịa & claim sai trước khi tới người duyệt |
| **Human-in-the-loop (HITL)** | luôn có *người thật* duyệt trước khi gửi — không auto-post |
| **StateGraph** | bản thiết kế graph trong LangGraph — nơi `add_node` / `add_edge` |
| **add_node / add_edge** | đặt một trạm lên bản đồ / nối đường ray cố định giữa 2 trạm |
| **add_conditional_edges** | nối đường *rẽ nhánh*: chạy router → đi trạm theo tên nó trả |
| **Router (route function)** | hàm đọc state → trả *tên trạm* đi tiếp (không ghi state) |
| **START / END** | điểm vào / điểm ra của graph |
| **compile()** | đóng gói StateGraph thành object chạy được (`.invoke(state)`) |

---

## 🤖 LLM / Prompt

| Thuật ngữ | Một câu |
|---|---|
| **Prompt** | đoạn text mình đưa cho LLM để nó xử lý |
| **System prompt** | phần đặt *vai trò + luật chơi* cho LLM ("mày là giám khảo, chỉ trả yes/no") |
| **User prompt** | phần *nội dung cụ thể* cần xử lý (câu hỏi + đoạn văn) |
| **Temperature** | độ "bay bổng" của LLM: 0.0 = quyết định/ổn định (classifier); cao = sáng tạo (viết văn) |
| **Deterministic** | cùng input luôn ra cùng output (nhờ temperature=0) |
| **Classifier** | máy phân loại — ở đây phân loại chunk thành CÓ/KHÔNG liên quan |
| **max_tokens** | giới hạn độ dài câu trả lời của LLM — nhỏ cho classifier để tiết kiệm |
| **Parse** | bóc tách output thô của LLM về dạng mình cần (vd "Yes." → `True`) |
| **Mock** | đồ giả lập thay cho thật khi test (vd LLM giả trả "yes" sẵn, khỏi gọi LLM thật) |

## 🐍 Code / Python

| Thuật ngữ | Một câu |
|---|---|
| **TypedDict** | khai báo "dict này có ô gì, mỗi ô kiểu gì" — chỉ là cái khuôn, không chứa logic |
| **DI (Dependency Injection)** | *tiêm* phụ thuộc từ ngoài vào thay vì để hàm/class tự tạo bên trong (dễ test, dễ thay) |
| **Factory** | một hàm *tạo ra và trả về* một hàm/đối tượng đã cấu hình sẵn |
| **Closure** | hàm bên trong "nhớ" được biến của hàm bao ngoài nó |
| **Protocol** | định nghĩa "phải có method gì" — không cần kế thừa, ai có đủ method là hợp |
| **Port / Adapter** | Port = ổ cắm (interface); Adapter = phích cắm thật (implementation) |
| **pool_size** | số chunk thô lấy *rộng* ra trước khi lọc — để có dư mà chọn |
| **async / await** | `async` = hàm có thể "chờ" việc chậm (gọi LLM/mạng) mà không khóa chương trình; `await` = chờ ở đây cho xong rồi lấy kết quả |
| **async lan truyền** | hàm gọi một thứ `async` (cần `await`) thì *chính nó* cũng phải `async` — async "lây" lên trên |
| **Hằng số module** | biến đặt ở đầu file (vd `_SYSTEM`), dùng chung, không đổi — `_` đầu tên = "nội bộ" |
| **Test** | đoạn code kiểm tra code khác chạy đúng |
| **assert** | "khẳng định phải đúng vầy" — sai thì test báo fail |
| **AsyncMock** | LLM/đồ giả phiên bản async — dặn sẵn `.return_value` cho nó trả |
| **asyncio.run(...)** | chạy một hàm `async` từ code thường, chờ và lấy kết quả |
| **pytest** | công cụ chạy test trong project |

---

## 🏛️ Kiến trúc & Dự án

| Thuật ngữ | Một câu |
|---|---|
| **Hexagonal architecture** | domain (logic thuần) ở giữa, thế giới ngoài cắm vào qua port — thay Qdrant/LLM không đụng logic |
| **Core vs Cloud** | Core = bộ não AI (MIT, niche-agnostic); Cloud = vỏ SaaS (auth/billing) gọi vào API của core |
| **Harvester** | bộ cào dữ liệu công khai (Phase 0) — không bao giờ gọi LLM |
| **Raw Data Lake** | vùng đổ dữ liệu *thô* sau khi cào, trước khi làm sạch |
| **TDD** | viết test *trước*, code *sau* (Red → Green → Refactor) |
| **LLMClientBase** | cổng duy nhất gọi LLM — cấm gọi `openai.*` trực tiếp |

---

## 🛡️ Production / An toàn (radar — học sau)

| Thuật ngữ | Một câu |
|---|---|
| **Prompt injection** | input độc (comment người lạ) lái LLM làm điều không nên |
| **PII** | thông tin cá nhân (SĐT, địa chỉ) — phải phát hiện & che |
| **Drift** | chất lượng/dữ liệu *trôi lệch* dần theo thời gian → phải đo mới biết |
| **Eval / RAGAS** | đo chất lượng RAG (faithfulness, relevancy, precision/recall) |
| **Freshness / recency** | độ *mới* của dữ liệu — quan trọng với tài chính/news |
| **MMR** | chọn kết quả *đa dạng*, tránh top-k toàn chunk gần trùng nhau |
| **Quantization** | nén model/vector cho nhẹ & nhanh, mất ít độ chính xác |
