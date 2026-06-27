"""BM25Index — In-memory sparse keyword search (Okapi BM25, Robertson et al. 1994).

VI: BM25 là thuật toán tìm kiếm từ khóa dùng trong Hybrid Search (Phase 3).
EN: BM25 is the sparse keyword retrieval algorithm used in Hybrid Search (Phase 3).

Ứng dụng / Application:
    HybridRetriever gọi BM25Index.search() song song với Qdrant dense search,
    sau đó dùng RRF để gộp 2 ranked list thành kết quả cuối.

    HybridRetriever calls BM25Index.search() in parallel with Qdrant dense search,
    then uses RRF to merge the 2 ranked lists into the final result.

Tại sao cần BM25 bên cạnh dense search? / Why BM25 alongside dense search?
    Dense search (bge-m3 + cosine) giỏi bắt ngữ nghĩa nhưng thất bại với từ khóa
    chính xác như "SPF 50+", "PA++++", mã sản phẩm, tên riêng.
    BM25 bắt chính xác những từ kỹ thuật đó.

    Dense search excels at semantic similarity but fails on exact keywords like
    "SPF 50+", product codes, proper nouns. BM25 catches those exactly.

Tại sao BM25 tốt hơn TF-IDF? / Why BM25 over TF-IDF?
    1. TF saturation (k1): doc có 100 lần "kem" không score cao hơn 50× doc có 2 lần.
       TF saturation (k1): doc with "kem" 100x doesn't score 50x higher than doc with 2x.
    2. Length normalization (b): doc dài không được lợi thế so với doc ngắn.
       Length normalization (b): long docs don't have an unfair advantage over short ones.

Công thức / Formula:
    score(d,t) = IDF(t) × TF×(k1+1) / (TF + k1×(1-b+b×dl/avgdl))
    IDF(t)     = log((N - df + 0.5) / (df + 0.5) + 1)

Tham số / Parameters:
    k1 = 1.5  → mức saturation TF / TF saturation level
    b  = 0.75 → mức chuẩn hóa độ dài / length normalization level

Xem thêm / See also: notes-knowledge.md §6 BM25
"""

import math
from dataclasses import dataclass, field  # 'dataclasses' có chữ 's' — không phải 'dataclass'


@dataclass
class BM25Index:
    # VI: k1 kiểm soát TF saturation — TF tăng nhưng score tiệm cận giới hạn (k1+1)
    # EN: k1 controls TF saturation — score asymptotes at (k1+1) as TF grows
    k1: float = 1.5

    # VI: b kiểm soát length normalization — 0=tắt, 1=chuẩn hóa hoàn toàn
    # EN: b controls length normalization — 0=off, 1=full normalization
    b: float = 0.75

    # VI: mutable default phải dùng field() — không được viết _docs: list = []
    # EN: mutable defaults require field() — writing _docs: list = [] raises ValueError
    _docs: list[dict] = field(default_factory=list)

    def add(self, doc_id: str, text: str, tenant_id: str) -> None:
        # VI: lowercase + split để tokenize — "Kem" và "kem" là cùng token
        # EN: lowercase + split for tokenization — "Kem" and "kem" match the same token
        tokens = text.lower().split()
        self._docs.append({
            "doc_id": doc_id,
            "text": text,
            "tenant_id": tenant_id,
            "tokens": tokens,  # VI: dùng để tính TF/IDF / EN: used to compute TF/IDF
        })

    def search(
        self,
        query: str,      # VI: câu query của user, không phải doc_id / EN: user query text, not a doc_id
        *,
        tenant_id: str,  # VI: keyword-only — bắt buộc gọi rõ tên / EN: keyword-only to prevent positional mistakes
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        # VI: chỉ tính BM25 trên docs của tenant này — isolation như Qdrant payload filter
        # EN: compute BM25 only on this tenant's docs — same isolation principle as Qdrant
        tenant_docs = [d for d in self._docs if d["tenant_id"] == tenant_id]
        if not tenant_docs:
            return []  # VI: guard — tránh chia cho 0 ở avgdl / EN: prevents divide-by-zero in avgdl

        # VI: avgdl = độ dài trung bình doc trong tenant, dùng cho length normalization
        # EN: avgdl = average doc length in this tenant, used for length normalization
        avgdl = sum(len(d["tokens"]) for d in tenant_docs) / len(tenant_docs)
        N = len(tenant_docs)            # VI: tổng docs trong tenant / EN: total docs in tenant
        terms = query.lower().split()   # VI: cùng tokenize với add() / EN: same tokenization as add()
        scores: list[tuple[str, float]] = []

        for doc in tenant_docs:
            score = 0.0
            doc_len = len(doc["tokens"])

            for term in terms:
                # VI: TF = số lần term xuất hiện trong doc này
                # EN: TF = number of times term appears in this doc
                tf = doc["tokens"].count(term)

                # VI: DF = số docs trong tenant chứa term — để tính IDF
                # EN: DF = number of tenant docs containing this term — used for IDF
                df = sum(1 for d in tenant_docs if term in d["tokens"])

                # VI: IDF cao = term hiếm = quan trọng hơn
                # EN: high IDF = rare term = more important signal
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1)

                # VI: BM25 score cho term này — cộng dồn qua tất cả terms trong query
                # EN: BM25 score for this term — accumulated across all query terms
                score += idf * (
                    (tf * (self.k1 + 1))
                    / (tf + self.k1 * (1 - self.b + self.b * (doc_len / avgdl)))
                )

            scores.append((doc["doc_id"], score))

        # VI: sort giảm dần rồi lấy top_k — RRF dùng thứ tự này làm ranked list
        # EN: sort descending then slice top_k — RRF uses this order as the ranked list
        return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]
