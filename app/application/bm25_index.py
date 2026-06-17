"""BM25Index — in-memory full-text search (Okapi BM25, Robertson et al. 1994).

Tại sao BM25?
- TF-IDF cơ bản không saturation TF: doc có 100 lần từ "python" vẫn
  chiếm ưu thế tuyệt đối so với doc có 5 lần. BM25 giải quyết bằng k1.
- BM25 chuẩn hóa theo độ dài doc (b parameter): doc ngắn không bị thiệt.

Công thức cho mỗi term t trong query:
    score(d, t) = IDF(t) × (TF(t,d) × (k1+1)) / (TF(t,d) + k1×(1-b+b×dl/avgdl))

- k1=1.5 : mức độ saturation TF (k1→∞ = TF-IDF thuần, k1=0 = chỉ dùng IDF)
- b=0.75  : mức độ chuẩn hóa độ dài (b=0 = không chuẩn hóa, b=1 = chuẩn hóa hoàn toàn)
"""

import math
from dataclasses import dataclass, field  # BUG FIX: thêm `field` — thiếu import gây NameError


@dataclass
class BM25Index:
    k1: float = 1.5
    b: float = 0.75
    _docs: list[dict] = field(default_factory=list)  # mutable default phải dùng field()

    def add(self, doc_id: str, text: str, tenant_id: str) -> None:
        tokens = text.lower().split()  # BUG FIX: lưu tokens vào dict thay vì vứt biến local
        self._docs.append({
            "doc_id": doc_id,
            "text": text,
            "tenant_id": tenant_id,
            "tokens": tokens,  # BUG FIX: thiếu key này → search không đọc được
        })

    def search(
        self,
        query: str,  # BUG FIX: param cũ là `doc_id` — search theo query text, không phải doc id
        *,
        tenant_id: str,
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        # BUG FIX: lấy TẤT CẢ docs của tenant, không tìm 1 doc theo id
        tenant_docs = [d for d in self._docs if d["tenant_id"] == tenant_id]
        if not tenant_docs:
            return []

        avgdl = sum(len(d["tokens"]) for d in tenant_docs) / len(tenant_docs)
        N = len(tenant_docs)
        terms = query.lower().split()
        scores: list[tuple[str, float]] = []  # BUG FIX: `scores = list[...] = []` là syntax error

        for doc in tenant_docs:  # BUG FIX: iterate tenant_docs (list), không phải query_doc (dict)
            score = 0.0
            doc_len = len(doc["tokens"])  # BUG FIX: key là "tokens" không phải "token"
            for term in terms:
                tf = doc["tokens"].count(term)
                df = sum(1 for d in tenant_docs if term in d["tokens"])
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
                score += idf * (
                    (tf * (self.k1 + 1))
                    / (tf + self.k1 * (1 - self.b + self.b * (doc_len / avgdl)))
                )
            scores.append((doc["doc_id"], score))

        return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]
