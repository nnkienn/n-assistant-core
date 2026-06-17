"""Reciprocal Rank Fusion — Cormack, Clarke, Buettcher (2009).

Tại sao dùng RRF thay vì trung bình điểm?
- Điểm dense (cosine similarity) và sparse (BM25) có scale hoàn toàn khác nhau.
  Không thể cộng trực tiếp: 0.95 cosine và 12.3 BM25 không có nghĩa gì cùng nhau.
- RRF chỉ dùng RANK (thứ hạng), không dùng điểm tuyệt đối → scale-invariant.

Công thức: RRF(d) = Σ_i  1 / (k + rank_i(d))
- k=60 là hằng số damping (từ paper gốc): làm mờ ưu thế của rank 1 so với rank 2.
  Nếu k=0: rank 1 được 1.0, rank 2 được 0.5 (gap lớn).
  Nếu k=60: rank 1 được 1/61≈0.016, rank 2 được 1/62≈0.016 (gap nhỏ hơn nhiều).
"""


def reciprocal_rank_fusion(  # BUG FIX: đổi tên từ `reciprocal_rank_factor` → `fusion`
    rank_lists: list[list[str]],  # BUG FIX: thiếu `]` đóng → SyntaxError
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    rrf_scores: dict[str, float] = {}
    for rank_list in rank_lists:
        for rank, doc_id in enumerate(rank_list, start=1):  # rank bắt đầu từ 1
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1 / (k + rank)
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
