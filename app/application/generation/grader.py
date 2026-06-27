"""RelevanceGrader — anh kiểm tra: chấm 1 đoạn văn CÓ/KHÔNG liên quan câu hỏi."""

from __future__ import annotations


# Lời dặn cố định cho AI: vai trò + luật chơi (chỉ trả yes/no).
_SYSTEM = (
    "Bạn là giám khảo đánh giá độ liên quan. Cho một câu hỏi và một đoạn văn, "
    "trả lời DUY NHẤT 'yes' nếu đoạn văn giúp trả lời câu hỏi, ngược lại 'no'. "
    "Không giải thích gì thêm."
)


class RelevanceGrader:

    def __init__(self, llm) -> None:
        self._llm = llm                    # AI thật, hoặc AI giả (mock) khi test

    async def grade(self, query: str, chunk_text: str) -> bool:
        # ── Bước 1: viết câu hỏi cụ thể cho AI ──
        user = (
            f"Câu hỏi: {query}\n\n"
            f"Đoạn văn: {chunk_text}\n\n"
            f"Đoạn văn này có giúp trả lời câu hỏi không? Chỉ trả lời 'yes' hoặc 'no'."
        )

        # ── Bước 2: gọi AI, lấy câu trả lời ──
        answer = await self._llm.chat(
            system=_SYSTEM,
            user=user,
            max_tokens=5,         # chỉ cần yes/no, không cho dài
            temperature=0.0,      # 0 = trả lời ổn định, không bay bổng
        )

        # ── Bước 3: "yes" → True, còn lại → False ──
        return answer.strip().lower().startswith("y")
