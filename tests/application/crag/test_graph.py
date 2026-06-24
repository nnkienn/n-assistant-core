"""Test end-to-end graph CRAG bằng đồ giả (fake) — thấy cả vòng lặp sống dậy.

Không cần Qdrant / LLM thật. Ta dựng kịch bản và kiểm tra graph chạy đúng:
lần đầu toàn rác → INCORRECT → correct quăng lưới rộng → grade lại ra hàng tốt → CORRECT.
"""

import asyncio

from app.application.crag.graph import build_crag_graph
from app.domain.ports.retriever import RetrievalHit


class FakeReranker:
    """Rerank giả: trả nguyên (passthrough), cắt còn top_k."""
    def rerank(self, query, hits, *, top_k):
        return hits[:top_k]


class FakeGrader:
    """Grader giả: chỉ chunk chứa chữ 'good' mới được chấm CÓ."""
    async def grade(self, query, text):
        return "good" in text


def test_loop_incorrect_roi_correct_thanh_CORRECT():
    class Retriever:
        # Lưới hẹp (lần đầu) → toàn rác; lưới rộng (correct, top_k>=60) → ra hàng tốt.
        def retrieve(self, query, *, tenant_id, top_k):
            if top_k >= 60:
                return [RetrievalHit("g1", "good: GPT-4 ~1.7 nghìn tỷ tham số", 1.0, "yt")]
            return [
                RetrievalHit("b1", "rác cảm ơn đã xem", 0.5, "yt"),
                RetrievalHit("b2", "rác like share", 0.4, "yt"),
            ]

    graph = build_crag_graph(retriever=Retriever(), reranker=FakeReranker(), grader=FakeGrader())

    initial = {"query": "GPT-4 bao nhiêu tham số?", "tenant_id": "tenant_demo", "top_k": 3}
    result = asyncio.run(graph.ainvoke(initial))

    assert result["verdict"] == "CORRECT"          # đã sửa sai thành công
    assert result["attempts"] == 1                 # tìm lại đúng 1 lần
    assert len(result["context"]) == 1             # bundle có 1 chunk tốt
    assert "good" in result["context"][0].text


def test_het_luot_van_rac_thi_dung_lai_khong_lap_vo_han():
    class AlwaysGarbage:
        def retrieve(self, query, *, tenant_id, top_k):
            return [RetrievalHit("b", "rác", 0.1, "yt")]

    graph = build_crag_graph(
        retriever=AlwaysGarbage(), reranker=FakeReranker(), grader=FakeGrader(), max_attempts=2
    )
    result = asyncio.run(graph.ainvoke({"query": "q", "tenant_id": "t", "top_k": 3}))

    assert result["verdict"] == "INCORRECT"        # tìm hoài vẫn rác
    assert result["attempts"] == 2                 # thử đúng max rồi DỪNG (chốt chặn)
    assert result["context"] == []                 # không có hàng → bundle rỗng (downstream abstain)
