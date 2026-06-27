# RAG Knowledge Notes — Phase 2 & 3
> Ghi lại WHY (tại sao code như vậy), không chỉ WHAT.
> Mỗi bước code = 1 section. Quiz sai → ghi thêm vào đây.
> Gặp thuật ngữ mới → thêm vào phần Glossary cuối file.

---

## Phase 2 — Vector Embedding & Storage

### Bước 1 — `domain/ports/embedder.py`

```python
class Embedder(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

**WHY batch `list[str]` → `list[list[float]]`:**
GPU xử lý song song. Ingest 1000 chunks mà gọi 1 lần từng text → chậm 10-50×. Gửi cả batch → GPU xử lý cùng lúc.

**WHY `Protocol` không phải `ABC`:**
Structural typing — class nào có đúng method `embed` là satisfy, không cần kế thừa. Swap `BGEEmbedder` → `MockEmbedder` trong test mà không chạm application layer.

**Quiz đã sai:**
- "L2-normalize để stable neuron" → SAI. Để cosine similarity = dot product. Qdrant tính cosine bằng dot product bên trong — chỉ đúng khi vector là unit vector (‖v‖ = 1).

---

### Bước 2 — `domain/ports/vector_store.py`

```python
@dataclass
class VectorSearchResult:
    id: str       # UUID5 — để lookup sau RRF
    score: float  # cosine similarity [0, 1]
    payload: dict # {"text": ..., "source": ..., "tenant_id": ...}

class VectorStore(Protocol):
    def ensure_collection(self, name: str, dim: int) -> None: ...
    def upsert(self, collection: str, vectors: list[list[float]], payloads: list[dict]) -> int: ...
    def search(self, collection: str, vector: list[float], *, tenant_id: str, top_k: int = 5) -> list[VectorSearchResult]: ...
```

**WHY `VectorSearchResult` không phải `RetrievalHit`:**
VectorStore là raw DB result — có `payload: dict` chưa có cấu trúc. `HybridRetriever` mới transform thành `RetrievalHit` sau RRF.

**WHY `payload: dict` không phải field cụ thể:**
VectorStore là domain port — không được biết application layer lưu gì. Hôm nay `{"text", "source"}`, mai thêm `{"language", "sentiment"}`. Hardcode field → phải sửa port mỗi lần (vi phạm Open/Closed).

**WHY `upsert()` trả `int`:**
Caller biết lưu được bao nhiêu chunks. `None` → không debug được khi ingest 0 chunk.

**WHY `*` trước `tenant_id`:**
Keyword-only → bắt buộc gọi rõ tên. `tenant_id` sai = data leak giữa tenants — security bug, không phải logic bug.

**WHY `ensure_collection(dim=1024)` phải đúng:**
Qdrant dùng `dim` để tạo HNSW index. Upsert vector sai dim → **Qdrant throw error ngay**, không phải "mất thông tin".

**WHY `search()` nhận 1 vector, không phải batch:**
User chỉ có 1 query tại 1 thời điểm. `embed()` nhận batch vì ingest nhiều chunk cùng lúc. Khác use case.

**Quiz đã sai:**
- "vectors là chunk băm ra" → SAI. `băm = hash` (deterministic, mất thông tin). Vector là **embedding** — learned representation, giữ ngữ nghĩa.
- "search nhận 1 vector để tránh loãng" → SAI. Vì user chỉ có 1 query tại 1 thời điểm.

---

### Bước 3 — `infrastructure/adapters/embedder/bge_embedder.py`

```python
from FlagEmbedding import FlagModel

class BGEEmbedder:
    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        self._model = FlagModel(model_name, use_fp16=True)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return vecs.tolist()
```

**WHY `use_fp16=True`:**
Float16 thay float32 → nửa RAM, nhanh hơn ~2×. Độ chính xác embedding gần như không đổi.

**WHY `normalize_embeddings=True`:**
L2-normalize → `‖v‖ = 1` → cosine similarity = dot product → Qdrant tính nhanh hơn, kết quả ổn định.

**WHY không kế thừa `Embedder`:**
`Embedder` là `Protocol` — structural typing. Có method `embed()` đúng signature là tự động satisfy. Không cần `class BGEEmbedder(Embedder)`.

---

### Bước 4 — `infrastructure/adapters/vectorstore/qdrant_store.py`

```python
id=str(uuid.uuid5(uuid.NAMESPACE_DNS, p.get("text","") + p.get("tenant_id","")))
```

**WHY ghép `text + tenant_id` không phải chỉ `text`:**
Cùng chunk "kem dưỡng da" có thể tồn tại ở 2 tenant. Chỉ dùng `text` → cùng UUID → tenant B upsert ghi đè data tenant A. Ghép `text + tenant_id` → UUID unique theo (nội dung, tenant).

**WHY `ensure_collection` check trước:**
Qdrant throw error nếu `create_collection()` khi collection đã tồn tại. Check `if name not in existing` để tránh crash.

**WHY filter `tenant_id` trước cosine (pre-filtering):**
Qdrant lọc tenant trước → chỉ tính cosine trên tập đã lọc → nhanh hơn nhiều. Filter sau = tính cosine toàn bộ mọi tenant → tốn tài nguyên vô ích.

**Quiz đã sai:**
- "ghép text+tenant_id vì uuid5 chứa namespace" → SAI. Vì cùng text tồn tại nhiều tenant.
- "bỏ check → duplicate vector" → SAI. Qdrant throw error crash chương trình.
- "filter chạy sau cosine" → SAI. Pre-filtering chạy TRƯỚC.

---

### Bước 5 — `application/ingestion/service.py` (IngestionService)

**Flow:**
```
load JSON → chunk_text() → [texts, payloads] → embed(batch) → ensure_collection → upsert → return count
```

**WHY guard `if not texts: return 0` trước embed:**
Nếu bỏ → `embed([])` trả `[]` → `len(vectors[0])` crash **IndexError** vì list rỗng không có `[0]`. Guard tránh crash, tránh gọi model vô ích.

**WHY `dim=len(vectors[0])` không hardcode `1024`:**
Đổi model từ bge-m3 (1024) sang model khác (768) → không cần sửa IngestionService. Hardcode → phải nhớ sửa mỗi lần đổi model.

**WHY DI (Dependency Injection) — ai quyết định inject gì:**
`main.py` (production) inject `BGEEmbedder + QdrantStore`. Test inject `MockEmbedder + MockStore`. `IngestionService` không biết đang dùng thật hay giả → dễ test, dễ swap.

**WHY `async def ingest_file`:**
Gọi `await embed()` bên trong → function cha phải `async`. async "lây" lên trên.

**Quiz đã sai:**
- "bỏ guard → tạo vector rỗng" → SAI. Crash IndexError tại `vectors[0]` vì list rỗng.
- "dim hardcode không sao" → SAI. Đổi model phải sửa tay, dễ quên.
- "không biết ai inject" → Composition Root: `main.py` hoặc test file quyết định.

---

## Công thức cốt lõi

```
# Cosine Similarity (L2-normalized)
cos(θ) = A · B = Σ(aᵢ × bᵢ)

# IDF (BM25 variant)
IDF(t) = log((N - df + 0.5) / (df + 0.5) + 1)

# BM25
score(d,t) = IDF(t) × TF×(k1+1) / (TF + k1×(1 - b + b×dl/avgdl))
  k1=1.5 → TF saturation (score tiệm cận, không tăng mãi)
  b=0.75 → length normalization (doc dài không lợi thế)

# RRF
RRF(d) = Σᵢ  1/(k + rankᵢ(d))    k=60
```

---

## Glossary — Thuật ngữ nhanh

| Thuật ngữ | Một câu |
|---|---|
| **Embedding** | biến text thành dãy số (vector) để máy so sánh *nghĩa* |
| **Vector** | dãy số (1024 chiều với bge-m3) đại diện nghĩa một đoạn text |
| **Chunk** | một mẩu văn bản nhỏ cắt ra từ tài liệu dài |
| **Cosine similarity** | đo độ giống về nghĩa bằng *góc* giữa 2 vector |
| **Dense retrieval** | tìm theo *nghĩa* bằng vector — giỏi ngữ nghĩa, dễ trượt từ khóa chính xác |
| **Sparse retrieval / BM25** | tìm theo *từ khóa* khớp chữ — bắt "SPF 50+", mã SKU |
| **Hybrid search** | dense + sparse → RRF → lấy điểm mạnh cả hai |
| **RRF** | gộp nhiều bảng xếp hạng bằng *thứ hạng*, không phải điểm tuyệt đối |
| **Rerank** | chấm lại top-k cho chính xác hơn sau retrieve |
| **Cross-encoder** | đọc query + doc *cùng nhau* → chính xác hơn, chậm hơn |
| **Bi-encoder** | encode query và doc *riêng lẻ* → nhanh, kém tinh hơn |
| **Qdrant** | vector database chuyên lưu & tìm vector |
| **Payload** | metadata kèm theo mỗi vector (text gốc, source, tenant_id) |
| **tenant_id** | nhãn ngăn cách dữ liệu từng kênh — mọi search bắt buộc lọc theo nó |
| **UUID5** | ID deterministic từ namespace + content → cùng chunk ingest 2 lần = overwrite, không duplicate |
| **HNSW** | thuật toán index của Qdrant — cần biết `dim` khi tạo collection |
| **Protocol** | "phải có method gì" — không cần kế thừa, có đủ method là hợp lệ |
| **Port / Adapter** | Port = interface (contract); Adapter = implementation thật |
| **DI (Dependency Injection)** | tiêm phụ thuộc từ ngoài vào, không để class tự tạo bên trong |
| **use_fp16** | dùng float16 thay float32 → nửa RAM, nhanh hơn ~2× |
| **normalize_embeddings** | L2-normalize → ‖v‖=1 → cosine = dot product |
| **CRAG** | RAG tự chấm điểm kết quả rồi sửa sai khi gặp rác |
| **LLM-as-judge** | dùng LLM làm giám khảo chấm điểm (yes/no liên quan) |
| **State machine** | chạy theo các trạm có thứ tự, mỗi trạm xử lý rồi chuyển tiếp |
| **Hallucination** | model bịa thông tin không có trong nguồn |
| **Grounding** | câu trả lời bám chặt vào nguồn dữ liệu thật |
| **fp16** | float16 — nửa độ chính xác của float32, đủ dùng cho embedding |
| **Structural typing** | match bằng cấu trúc (có method gì), không phải bằng kế thừa |
| **keyword-only argument** | tham số sau `*` — bắt buộc gọi với tên, không nhầm thứ tự |
| **Open/Closed principle** | mở để mở rộng, đóng để sửa — không sửa port khi thêm field |
| **VectorSearchResult** | raw result từ Qdrant — có id, score, payload dict chưa structured |
| **RetrievalHit** | output đã xử lý sau RRF — có doc_id, text, score, source rõ ràng |
