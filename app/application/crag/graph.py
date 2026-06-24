"""build_crag_graph — ráp các node thành state machine CRAG hoàn chỉnh."""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from app.application.crag.state import CRAGState
from app.application.crag.node import (
    make_retrieve_node, make_grade_node, make_correct_node,
    decide_node, finalize_node,
)
from app.application.crag.decision import make_router


def build_crag_graph(*, retriever, reranker, grader, max_attempts: int = 2):
    g = StateGraph(CRAGState)                       # khai báo graph dùng tờ giấy CRAGState

    # ── 1. Đăng ký các trạm (node) ──
    g.add_node("retrieve", make_retrieve_node(retriever, reranker))
    g.add_node("grade",    make_grade_node(grader))
    g.add_node("decide",   decide_node)
    g.add_node("correct",  make_correct_node(retriever))
    g.add_node("finalize", finalize_node)

    # ── 2. Nối đường ray cố định (edge) ──
    g.add_edge(START, "retrieve")                   # vào → retrieve
    g.add_edge("retrieve", "grade")                 # retrieve → grade
    g.add_edge("grade", "decide")                   # grade → decide

    # ── 3. Bẻ ghi sau decide (conditional edge) ──
    g.add_conditional_edges("decide", make_router(max_attempts), {
        "correct":  "correct",                      # router nói "correct" → đi trạm correct
        "finalize": "finalize",                     # router nói "finalize" → đi trạm finalize
    })

    # ── 4. Hai đường còn lại ──
    g.add_edge("correct", "grade")                  # correct → QUAY LẠI grade (vòng lặp!)
    g.add_edge("finalize", END)                     # finalize → xong

    return g.compile()                              # đóng gói thành graph chạy được
