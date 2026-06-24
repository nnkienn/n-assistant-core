from __future__ import annotations

_CORRECT_RATIO  = 0.5

def decide_verdict(n_relevant : int , n_candidates : int )-> str:
    if(n_candidates == 0 or n_relevant == 0):
        return "INCORRECT"
    if(n_relevant / n_candidates >= _CORRECT_RATIO):
        return "CORRECT"
    return "AMBIGUOUS"

def make_router(max_attempts: int = 2):
    """Nhìn verdict + attempts → quyết định đi trạm nào tiếp."""

    def route(state) -> str:
        if state["verdict"] == "INCORRECT" and state.get("attempts", 0) < max_attempts:
            return "correct"     # còn rác & chưa thử quá nhiều → tìm lại
        return "finalize"        # đủ tốt, HOẶC đã thử hết lượt → chốt

    return route
