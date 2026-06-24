"""Các node của graph CRAG (Phase 3).

Node = hàm: đọc state → làm việc → trả về DICT phần state cần ghi.
LangGraph merge dict đó vào state chung. Node KHÔNG tự tạo dependency —
được tiêm qua factory (make_*_node), giống DI của HybridRetriever.
"""

from __future__ import annotations

from app.application.crag.state import CRAGState
from app.application.crag.decision import decide_verdict   # thêm ở đầu file


def make_retrieve_node(retriever, reranker, *, pool_size: int = 20):
    """Trả về retrieve_node đã gắn sẵn retriever + reranker.

    pool_size: số chunk thô lấy rộng từ Hybrid trước khi rerank — rộng để
               grade còn 'nguyên liệu' mà xoay, đúng tinh thần CRAG.
    """

    def retrieve_node(state: CRAGState) -> dict:
        query     = state["query"]
        tenant_id = state["tenant_id"]
        top_k     = state["top_k"]

        # ── Hybrid lấy rộng (pool_size) → Rerank lọc xuống candidate ──
        # Rerank chạy TRƯỚC grade: nó rẻ (cross-encoder) so với mỗi lần
        # gọi LLM grade → pre-filter để LLM khỏi phải chấm rác hiển nhiên.
        raw        = retriever.retrieve(query, tenant_id=tenant_id, top_k=pool_size)
        candidates = reranker.rerank(query, raw, top_k=top_k * 2)

        # Chỉ trả ô mình ghi — phần còn lại của state giữ nguyên.
        return {"candidates": candidates}

    return retrieve_node


def make_grade_node(grader):
    """Trả về grade_node đã gắn sẵn grader (anh kiểm tra)."""

    async def grade_node(state: CRAGState) -> dict:
        query = state["query"]
        relevant = []

        # Lặp qua từng chunk thô, chấm CÓ/KHÔNG, chỉ giữ cái CÓ.
        for hit in state["candidates"]:
            if await grader.grade(query, hit.text):   # await: chờ chấm xong
                relevant.append(hit)

        # Ghi ô relevant; candidates/query… giữ nguyên.
        return {"relevant": relevant}

    return grade_node


def decide_node(state: CRAGState) -> dict:
    """Điền ô verdict từ số chunk tốt / tổng."""
    verdict = decide_verdict(len(state["relevant"]), len(state["candidates"]))
    return {"verdict": verdict}


def finalize_node(state: CRAGState) -> dict:
    """Bundle sạch cuối cùng: lấy top_k chunk tốt nhất đã grade."""
    return {"context": state["relevant"][: state["top_k"]]}


def make_correct_node(retriever, *, wide_pool: int = 60):
    """Trả về correct_node: tìm lại RỘNG HƠN trong cùng kho (không ra web)."""

    def correct_node(state: CRAGState) -> dict:
        # Quăng lưới rộng hơn nhiều (wide_pool) để vớt chunk tốt nằm sâu.
        wider = retriever.retrieve(
            state["query"], tenant_id=state["tenant_id"], top_k=wide_pool
        )
        # Ghi đè candidates → grade_node sẽ chấm lại mẻ rộng này.
        # Tăng attempts để chốt chặn biết đã thử thêm 1 lần.
        return {
            "candidates": wider,
            "attempts": state.get("attempts", 0) + 1,
        }

    return correct_node