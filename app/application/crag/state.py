"""CRAGState — tờ giấy trạng thái chạy qua graph CRAG (Phase 3).

Mỗi node đọc vài ô, ghi vài ô. TypedDict = chỉ khai báo "tờ giấy có ô gì",
không chứa logic. LangGraph merge phần dict mỗi node trả về vào state chung.
"""

from __future__ import annotations

from typing import TypedDict

from app.domain.ports.retriever import RetrievalHit


class CRAGState(TypedDict):
    # ── Input: caller đặt vào lúc khởi chạy ──────────────────────────
    query: str          # câu hỏi của khán giả
    tenant_id: str      # namespace của kênh — bắt buộc, mọi search lọc theo nó
    top_k: int          # số chunk sạch muốn lấy cuối cùng

    # ── Trung gian: các node ghi dần vào ─────────────────────────────
    candidates: list[RetrievalHit]   # retrieve_node ghi: kết quả thô từ Hybrid+Rerank
    relevant: list[RetrievalHit]     # grade_node ghi: chỉ những chunk được chấm "CÓ liên quan"
    verdict: str                     # decision ghi: "CORRECT" | "AMBIGUOUS" | "INCORRECT"
    attempts: int                    # số lần đã tìm lại — chặn lặp vô hạn
    # ── Output: bundle sạch giao cho bước sau (Creator) ──────────────
    context: list[RetrievalHit]      # kết quả cuối, đã qua sửa sai nếu cần
